import asyncio
import time
import uuid
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


def create_agent(session_id: str = "") -> OrchestratorAgent:
    """Cria orchestrator isolado por conexão WebSocket. Roteia para especialista automaticamente."""
    tools = load_tools()
    return OrchestratorAgent(llm=llm, all_tools=tools, session_id=session_id)


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


@app.get("/metrics")
async def get_metrics():
    import subprocess as _sp
    from audit import tool_stats as _tool_stats
    import tracing as _tracing
    import circuit_breaker as _circuit_breaker
    from knowledge_graph import KnowledgeGraph as _KnowledgeGraph

    # VRAM via nvidia-smi
    vram: dict = {}
    try:
        out = _sp.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total,memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        parts = [x.strip() for x in out.split(",")]
        used, total, free = int(parts[0]), int(parts[1]), int(parts[2])
        vram = {"used_mb": used, "total_mb": total, "free_mb": free,
                "pct": round(used / total * 100, 1) if total else 0}
    except Exception:
        pass

    try:
        kg_stats = _KnowledgeGraph().stats()
    except Exception:
        kg_stats = {"entities": 0, "relations": 0}

    return {
        "inference": {
            "tps":               llm.session_tokens.get("tps", 0),
            "ttft_ms":           llm.session_tokens.get("ttft_ms", 0),
            "context_pct":       llm.session_tokens.get("context_pct", 0),
            "prompt_tokens":     llm.session_tokens.get("prompt", 0),
            "completion_tokens": llm.session_tokens.get("completion", 0),
        },
        "tools":           _tool_stats(days=7),
        "llm_calls":       _tracing.stats(days=1),
        "circuit_breaker": _circuit_breaker.status(),
        "knowledge_graph": kg_stats,
        "vram":            vram,
    }


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
            "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw,power.limit",
            "--format=csv,noheader,nounits"
        ], capture_output=True, text=True, timeout=5).stdout.strip()
        p   = [x.strip() for x in out.split(",")]
        gpu = {"name": p[0], "temp": p[1], "util": p[2],
               "vram_used": p[3], "vram_total": p[4],
               "power_draw": p[5] if len(p) > 5 else "N/A",
               "power_limit": p[6] if len(p) > 6 else "N/A"}
    except Exception:
        gpu = {}
    return {"ollama": ollama, "gpu": gpu}


@app.get("/sandbox/status")
async def sandbox_status():
    from tools.run_python_tool import get_sandbox_status
    return get_sandbox_status()


@app.get("/workspace/img/{filepath:path}")
async def serve_workspace_image(filepath: str):
    import re
    import os
    # permite subpastas de 1 nivel (ex: "charts/foo.png") sem abrir path traversal —
    # cada segmento so aceita \w/-, "." nao entra em segmento (bloqueia "..")
    if not re.match(r'^[\w\-]+(/[\w\-]+)*\.(png|jpg|jpeg|webp|gif|bmp)$', filepath):
        raise HTTPException(status_code=400, detail="Caminho invalido")
    workspace_dir = os.path.join(os.path.dirname(__file__), "workspace")
    path = os.path.normpath(os.path.join(workspace_dir, filepath))
    if not path.startswith(os.path.normpath(workspace_dir) + os.sep):
        raise HTTPException(status_code=400, detail="Caminho invalido")
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Imagem nao encontrada")
    ext  = filepath.rsplit(".", 1)[-1].lower()
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
            "webp": "image/webp", "gif": "image/gif", "bmp": "image/bmp"}.get(ext, "image/png")
    return FileResponse(path, media_type=mime)


def _build_conversation_markdown(title: str, messages: list) -> str:
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "---",
        f"criado: {now}",
        "tags: [agente-ia, conversa]",
        f"mensagens: {len(messages)}",
        "---",
        "",
        f"# {title}",
        "",
        f"**Exportado em:** {now}  ",
        f"**Mensagens:** {len(messages)}",
        "",
    ]
    for m in messages:
        role = "Usuário" if m.get("role") == "user" else "Agente"
        content = str(m.get("content", "")).strip()
        lines.append(f"## {role}")
        lines.append("")
        lines.append(content)
        lines.append("")
    return "\n".join(lines)


@app.post("/export/conversation")
async def export_conversation(body: dict, _rl=Depends(_check_rate_limit)):
    """Exporta a conversa atual (mensagens vêm do frontend, que já mantém o
    histórico completo) pra markdown. Sempre retorna o markdown pro frontend
    baixar como arquivo, e tenta salvar uma cópia no Obsidian (best-effort —
    segue o mesmo padrão silencioso de memory.py._export_to_obsidian)."""
    import os
    import re
    import logging
    from datetime import datetime
    from config import OBSIDIAN_BASE, link_note_in_conversas_index

    title = str(body.get("title") or "Conversa").strip()
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise HTTPException(status_code=400, detail="'messages' vazio ou inválido")

    markdown = _build_conversation_markdown(title, messages)
    safe_title = re.sub(r'[<>:"/\\|?*]', '', title)[:60].strip() or "conversa"
    filename = f"{safe_title}.md"

    obsidian_path = None
    try:
        conv_dir = os.path.join(OBSIDIAN_BASE, "Gabriel", "Projetos", "Agente IA Local", "Conversas")
        os.makedirs(conv_dir, exist_ok=True)
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        out_name = f"{date_prefix} — {safe_title}.md"
        filepath = os.path.join(conv_dir, out_name)
        if os.path.exists(filepath):
            hour_suffix = datetime.now().strftime("%Hh%M")
            out_name = f"{date_prefix} — {safe_title} ({hour_suffix}).md"
            filepath = os.path.join(conv_dir, out_name)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(markdown)
        link_note_in_conversas_index(conv_dir, out_name)
        obsidian_path = filepath
        filename = out_name
    except Exception as e:
        logging.getLogger(__name__).warning("export_conversation: falha ao salvar no Obsidian: %s", e)

    return {
        "markdown": markdown,
        "filename": filename,
        "obsidian_saved": obsidian_path is not None,
        "obsidian_path": obsidian_path,
    }


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), _rl=Depends(_check_rate_limit)):
    import os
    from rag import get_rag_index
    safe = os.path.basename(file.filename or "arquivo")
    dest = os.path.join(os.path.dirname(__file__), "workspace", safe)
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


@app.post("/rag/index-folder")
async def rag_index_folder(body: dict, _rl=Depends(_check_rate_limit)):
    from rag import get_rag_index
    folder    = body.get("path", "").strip()
    recursive = bool(body.get("recursive", False))
    if not folder:
        raise HTTPException(status_code=400, detail="path obrigatório")
    results = await asyncio.get_running_loop().run_in_executor(
        executor, lambda: get_rag_index().index_folder(folder, recursive)
    )
    return {"results": results, "total": len(results)}


@app.post("/rag/index-file")
async def rag_index_file(body: dict, _rl=Depends(_check_rate_limit)):
    from rag import get_rag_index
    path = body.get("path", "").strip()
    if not path:
        raise HTTPException(status_code=400, detail="path obrigatório")
    result = await asyncio.get_running_loop().run_in_executor(
        executor, lambda: get_rag_index().index_file(path)
    )
    return result


@app.delete("/rag/docs/{fname}")
async def rag_delete_doc(fname: str):
    from rag import get_rag_index
    return get_rag_index().delete_doc(fname)


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


@app.get("/templates")
async def get_templates():
    from templates import list_templates
    return {"templates": list_templates()}


@app.get("/templates/{template_id}")
async def get_template(template_id: str):
    from templates import get_template as _get
    tmpl = _get(template_id)
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    return tmpl


@app.get("/specialist-models")
async def get_specialist_models():
    from orchestrator import list_specialist_models, SPECIALISTS
    models_data = list_specialist_models()
    return {
        "specialists": [
            {"key": k, "label": SPECIALISTS[k]["label"], "model": models_data[k]}
            for k in SPECIALISTS
        ]
    }


@app.post("/specialist-models")
async def post_specialist_model(body: dict, _rl=Depends(_check_rate_limit)):
    from orchestrator import SPECIALISTS, set_specialist_model
    specialist = body.get("specialist", "").strip()
    model      = body.get("model", "").strip()
    if specialist not in SPECIALISTS:
        raise HTTPException(status_code=400, detail=f"Especialista '{specialist}' desconhecido")
    if not model:
        raise HTTPException(status_code=400, detail="model obrigatório")
    set_specialist_model(specialist, model)
    return {"specialist": specialist, "model": model}


@app.get("/kg/stats")
async def kg_stats():
    from knowledge_graph import KnowledgeGraph
    return KnowledgeGraph().stats()


@app.get("/kg/query")
async def kg_query(topic: str = "", limit: int = 20):
    from knowledge_graph import KnowledgeGraph
    kg = KnowledgeGraph()
    return {"topic": topic, "facts": kg.query(topic, max_results=min(limit, 50))}


@app.post("/kg/consolidate")
async def kg_consolidate(max_age_days: int = 90, min_count: int = 2):
    from knowledge_graph import KnowledgeGraph
    kg = KnowledgeGraph()
    return kg.consolidate(max_age_days=max_age_days, min_count=min_count)


@app.get("/trace/llm/stats")
async def trace_llm_stats(days: int = 1):
    import tracing
    return tracing.stats(days=days)


@app.get("/trace/llm/recent")
async def trace_llm_recent(limit: int = 50):
    import tracing
    return tracing.recent(limit=min(limit, 200))


@app.get("/circuit-breaker/status")
async def circuit_breaker_status():
    import circuit_breaker
    return circuit_breaker.status()


@app.post("/circuit-breaker/reset")
async def circuit_breaker_reset(tool: str = ""):
    import circuit_breaker
    circuit_breaker.reset(tool or None)
    return {"reset": tool or "all"}


@app.get("/memory/short-term/{session_id}")
async def memory_short_term(session_id: str):
    from memory import Memory
    m = Memory()
    return {"messages": m.short_term.get_messages(session_id)}


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
    if "tech_level" in updates and updates["tech_level"] != p.data.get("tech_level"):
        # escolha manual do usuário — para de sobrescrever com auto-detecção
        updates["tech_level_auto"] = False
    if isinstance(body.get("tech_level_auto"), bool):
        updates["tech_level_auto"] = body["tech_level_auto"]
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

    session_id = str(uuid.uuid4())
    agent = create_agent(session_id)
    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "cancel":
                agent.cancel()
                continue

            task = data.get("task", "").strip()
            template_id     = data.get("template_id", "").strip()
            template_inputs = data.get("template_inputs", {})

            if template_id and isinstance(template_inputs, dict):
                from templates import build_task as _build
                built = _build(template_id, template_inputs)
                if built:
                    task = built

            if not task:
                continue

            loop = asyncio.get_running_loop()
            queue = asyncio.Queue()
            agent.reset_cancel()

            def sync_callback(step_data):
                asyncio.run_coroutine_threadsafe(queue.put(step_data), loop)

            def run_agent():
                llm.reset_tokens()
                timer = threading.Timer(TASK_TIMEOUT, lambda: agent.cancel(reason="timeout"))
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
                        if isinstance(msg, dict):
                            if msg.get("type") == "cancel":
                                agent.cancel()
                            elif msg.get("type") == "hitl_response":
                                from agent import _HITL_REGISTRY
                                hitl_id = msg.get("id", "")
                                entry   = _HITL_REGISTRY.get(hitl_id)
                                if entry:
                                    entry["approved"] = bool(msg.get("approved", False))
                                    entry["event"].set()
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
        agent.memory.end_session(session_id, llm)


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    target = _frontend_out / full_path
    if target.is_file():
        return FileResponse(str(target))
    idx = _frontend_out / "index.html"
    if idx.exists():
        return FileResponse(str(idx))
    raise HTTPException(status_code=404, detail="Not found")
