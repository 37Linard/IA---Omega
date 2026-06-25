import asyncio
import time
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
import secrets
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends, HTTPException, UploadFile, File
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
import voice

import logging
import threading
from config import OLLAMA_MODEL, OLLAMA_URL, TASK_TIMEOUT, AUTH_PASSWORD, SCHEDULED_TASKS, RATE_LIMIT_REQUESTS, RATE_LIMIT_WINDOW
import auth as _auth
import scheduler as _scheduler
import watcher as _watcher
import audit as _audit

# ---- Rate limiting ----
_rl_buckets: dict[str, list[float]] = defaultdict(list)

def _check_rate_limit(request: Request):
    if not RATE_LIMIT_REQUESTS:
        return
    ip  = request.client.host if request.client else "unknown"
    now = time.monotonic()
    _rl_buckets[ip] = [t for t in _rl_buckets[ip] if now - t < RATE_LIMIT_WINDOW]
    if len(_rl_buckets[ip]) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(status_code=429, detail=f"Rate limit: {RATE_LIMIT_REQUESTS} req/{RATE_LIMIT_WINDOW}s")
    _rl_buckets[ip].append(now)

# Buffer de logs para o frontend
_log_buffer = deque(maxlen=200)

class _FrontendLogHandler(logging.Handler):
    def emit(self, record):
        from datetime import datetime
        _log_buffer.append({
            "t":     datetime.fromtimestamp(record.created).strftime("%H:%M:%S"),
            "level": record.levelname,
            "msg":   record.getMessage()
        })

_fh = _FrontendLogHandler()
_fh.setLevel(logging.INFO)
logging.getLogger().addHandler(_fh)
from llm import OllamaLLM
from orchestrator import OrchestratorAgent
from tool_loader import load_tools

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_security = HTTPBasic(auto_error=False)

def check_auth(credentials: HTTPBasicCredentials = Depends(_security)):
    if not AUTH_PASSWORD:
        return
    if credentials is None or not secrets.compare_digest(
        credentials.password.encode(), AUTH_PASSWORD.encode()
    ):
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": "Basic"})

app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve Next.js static assets (built via `npm run build`)
from pathlib import Path as _Path
_frontend_out = _Path(__file__).parent / "frontend" / "out"
_next_dir = _frontend_out / "_next"
if _next_dir.exists():
    app.mount("/_next", StaticFiles(directory=str(_next_dir)), name="nextjs_static")

llm      = OllamaLLM(model=OLLAMA_MODEL)
executor = ThreadPoolExecutor(max_workers=4)


def create_agent() -> OrchestratorAgent:
    """Cria orchestrator isolado por conexão WebSocket. Roteia para especialista automaticamente."""
    tools = load_tools()
    return OrchestratorAgent(llm=llm, all_tools=tools)


_scheduler.start(create_agent, SCHEDULED_TASKS)
_watcher.start()


@app.post("/login")
async def login(body: dict):
    token = _auth.create_token(body.get("password", ""))
    if not token:
        raise HTTPException(status_code=401, detail="Senha incorreta")
    return {"token": token}


@app.get("/")
async def root():
    idx = _frontend_out / "index.html"
    if idx.exists():
        return FileResponse(str(idx))
    return FileResponse("static/index.html")


@app.get("/audit")
async def get_audit(limit: int = 100, tool: str = "", _rl=Depends(_check_rate_limit)):
    return {"entries": _audit.query(limit=min(limit, 500), tool_filter=tool)}


@app.get("/analyze")
async def analyze_errors(_rl=Depends(_check_rate_limit)):
    import os, json as _json
    error_file = os.path.join(os.path.dirname(__file__), "workspace", "error_log.json")
    try:
        with open(error_file, "r", encoding="utf-8") as f:
            errors = _json.load(f).get("errors", [])
    except Exception:
        return {"analysis": "Nenhum erro registrado ainda.", "count": 0}
    if not errors:
        return {"analysis": "Nenhum erro registrado ainda.", "count": 0}
    summary = "\n".join(
        f"[{e['timestamp'][:10]}] {e['type']}: {e['details']}"
        for e in errors[-20:]
    )
    prompt = (
        "Analise os erros abaixo de um agente IA ReAct e sugira melhorias no prompt ou código:\n\n"
        + summary + "\n\nSugestões práticas:"
    )
    analysis = await asyncio.get_running_loop().run_in_executor(executor, llm.generate, prompt)
    return {"analysis": analysis, "count": len(errors)}


@app.get("/logs")
async def get_logs():
    return list(_log_buffer)


@app.get("/models")
async def list_models():
    import requests as req
    try:
        r      = req.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        models = [m["name"] for m in r.json().get("models", [])]
        return {"models": models, "current": llm.model}
    except Exception:
        return {"models": [llm.model], "current": llm.model}


@app.post("/model")
async def set_model(body: dict):
    name = body.get("model", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="model required")
    llm.model = name
    log.info("Modelo trocado para: %s", name)
    return {"model": llm.model}


@app.get("/health")
async def get_health():
    import subprocess, requests as req
    # Ollama
    try:
        r      = req.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        models = [m["name"] for m in r.json().get("models", [])]
        ollama = {"ok": True, "models": models}
    except Exception:
        ollama = {"ok": False, "models": []}
    # GPU via nvidia-smi
    gpu = {}
    try:
        out = subprocess.run([
            "nvidia-smi",
            "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total",
            "--format=csv,noheader,nounits"
        ], capture_output=True, text=True, timeout=5).stdout.strip()
        p   = [x.strip() for x in out.split(",")]
        gpu = {"name": p[0], "temp": p[1], "util": p[2],
               "vram_used": p[3], "vram_total": p[4]}
    except Exception:
        gpu = {}
    return {"ollama": ollama, "gpu": gpu}


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), _rl=Depends(_check_rate_limit)):
    import os
    from rag import get_rag_index
    safe = os.path.basename(file.filename or "arquivo")
    dest = os.path.join(r"C:\Users\User\Desktop\MEU\IA\workspace", safe)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    response = {"path": dest, "name": safe, "size": len(content)}
    if safe.lower().endswith(".pdf"):
        try:
            result = await asyncio.get_running_loop().run_in_executor(
                executor, get_rag_index().index_pdf, dest
            )
            response["rag"] = result
        except Exception as e:
            response["rag"] = {"status": "error", "error": str(e)}
    return response


@app.get("/rag/docs")
async def rag_list_docs():
    from rag import get_rag_index
    return {"docs": get_rag_index().list_docs()}


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    audio = await file.read()
    text  = await asyncio.get_running_loop().run_in_executor(executor, voice.transcribe, audio)
    return {"text": text}


@app.post("/speak")
async def speak_text(body: dict):
    text  = body.get("text", "")[:500]
    audio = await asyncio.get_running_loop().run_in_executor(executor, voice.speak, text)
    return Response(content=audio, media_type="audio/wav")


@app.get("/history")
async def get_history(credentials: HTTPBasicCredentials = Depends(check_auth)):
    from memory import Memory
    m = Memory()
    return {"sessions": m.data.get("sessions", [])}


@app.get("/profile")
async def get_profile():
    from user_profile import UserProfile
    return UserProfile().to_dict()


@app.post("/profile")
async def update_profile(body: dict, _rl=Depends(_check_rate_limit)):
    from user_profile import UserProfile
    p = UserProfile()
    allowed = {"name", "tech_level", "tone", "language"}
    updates = {k: v for k, v in body.items() if k in allowed and isinstance(v, str)}
    if updates:
        p.update(**updates)
    return p.to_dict()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Verifica JWT no primeiro pacote se auth ativado
    if AUTH_PASSWORD:
        try:
            first = await asyncio.wait_for(websocket.receive_json(), timeout=10)
            if not _auth.verify_token(first.get("token", "")):
                await websocket.send_json({"type": "error", "content": "Não autorizado — faça login."})
                await websocket.close(code=4001)
                return
        except Exception:
            await websocket.close(code=4001)
            return

    agent = create_agent()
    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "cancel":
                agent.cancel()
                continue

            task = data.get("task", "").strip()
            if not task:
                continue

            loop = asyncio.get_running_loop()
            queue = asyncio.Queue()
            agent.reset_cancel()

            def sync_callback(step_data):
                asyncio.run_coroutine_threadsafe(queue.put(step_data), loop)

            def run_agent():
                llm.reset_tokens()
                timer = threading.Timer(TASK_TIMEOUT, lambda: agent.cancel())
                timer.start()
                try:
                    agent.run(task, step_callback=sync_callback)
                except Exception as e:
                    asyncio.run_coroutine_threadsafe(
                        queue.put({"type": "error", "content": str(e)}), loop
                    )
                finally:
                    timer.cancel()
                    tok = llm.session_tokens
                    asyncio.run_coroutine_threadsafe(
                        queue.put({"type": "token_usage",
                                   "prompt": tok["prompt"],
                                   "completion": tok["completion"]}), loop
                    )
                    asyncio.run_coroutine_threadsafe(
                        queue.put({"type": "done", "content": ""}), loop
                    )

            loop.run_in_executor(executor, run_agent)

            ws_fut = None
            done = False
            while not done:
                q_fut = asyncio.ensure_future(queue.get())
                if ws_fut is None or ws_fut.done():
                    ws_fut = asyncio.ensure_future(websocket.receive_json())

                finished, _ = await asyncio.wait([q_fut, ws_fut], return_when=asyncio.FIRST_COMPLETED)

                if ws_fut in finished:
                    try:
                        msg = ws_fut.result()
                        if isinstance(msg, dict) and msg.get("type") == "cancel":
                            agent.cancel()
                    except Exception:
                        pass
                    ws_fut = None

                if q_fut in finished:
                    item = q_fut.result()
                    await websocket.send_json(item)
                    if item.get("type") == "done":
                        done = True
                else:
                    q_fut.cancel()

            if ws_fut and not ws_fut.done():
                ws_fut.cancel()
                try:
                    await ws_fut
                except (asyncio.CancelledError, Exception):
                    pass

    except WebSocketDisconnect:
        agent.cancel()


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    target = _frontend_out / full_path
    if target.is_file():
        return FileResponse(str(target))
    idx = _frontend_out / "index.html"
    if idx.exists():
        return FileResponse(str(idx))
    raise HTTPException(status_code=404, detail="Not found")
