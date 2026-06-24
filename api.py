import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from llm import OllamaLLM
from agent import ReActAgent
from tools.echo_tool import EchoTool
from tools.read_file_tool import ReadFileTool
from tools.write_file_tool import WriteFileTool
from tools.list_directory_tool import ListDirectoryTool
from tools.web_search_tool import WebSearchTool
from tools.http_request_tool import HttpRequestTool
from tools.run_python_tool import RunPythonTool
from tools.get_currency_tool import GetCurrencyTool
from tools.fetch_page_tool import FetchPageTool
from tools.save_note_tool import SaveNoteTool

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

llm = OllamaLLM(model="llama3.2:3b")
tools = [
    EchoTool(),
    ReadFileTool(),
    WriteFileTool(),
    ListDirectoryTool(),
    WebSearchTool(),
    HttpRequestTool(),
    RunPythonTool(),
    GetCurrencyTool(),
    FetchPageTool(),
    SaveNoteTool(),
]
agent = ReActAgent(llm=llm, tools=tools)
executor = ThreadPoolExecutor(max_workers=1)


@app.get("/")
async def root():
    return FileResponse("static/index.html")


@app.get("/history")
async def get_history():
    from memory import Memory
    m = Memory()
    return {"sessions": m.data.get("sessions", [])}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            task = data.get("task", "").strip()
            if not task:
                continue

            loop = asyncio.get_event_loop()
            queue = asyncio.Queue()

            def sync_callback(step_data):
                asyncio.run_coroutine_threadsafe(queue.put(step_data), loop)

            def run_agent():
                try:
                    agent.run(task, step_callback=sync_callback)
                except Exception as e:
                    asyncio.run_coroutine_threadsafe(
                        queue.put({"type": "error", "content": str(e)}), loop
                    )
                finally:
                    asyncio.run_coroutine_threadsafe(
                        queue.put({"type": "done", "content": ""}), loop
                    )

            loop.run_in_executor(executor, run_agent)

            while True:
                item = await queue.get()
                await websocket.send_json(item)
                if item.get("type") == "done":
                    break

    except WebSocketDisconnect:
        pass
