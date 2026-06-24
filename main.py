from llm import OllamaLLM
from agent import ReActAgent
from tools.echo_tool import EchoTool
from tools.read_file_tool import ReadFileTool
from tools.web_search_tool import WebSearchTool
from tools.run_python_tool import RunPythonTool
from tools.write_file_tool import WriteFileTool
from tools.list_directory_tool import ListDirectoryTool
from tools.http_request_tool import HttpRequestTool


def main():
    llm = OllamaLLM(model="llama3.1:8b")

    tools = [
        EchoTool(),
        ReadFileTool(),
        WriteFileTool(),
        ListDirectoryTool(),
        WebSearchTool(),
        HttpRequestTool(),
        RunPythonTool(),
    ]

    agent = ReActAgent(llm=llm, tools=tools)

    print("=== AGENTE IA LOCAL ===")
    print("Modelo: llama3.1:8b | Ferramentas:", [t.name for t in tools])
    print("Digite 'sair' para encerrar.\n")

    while True:
        tarefa = input("Tarefa: ").strip()
        if tarefa.lower() in ("sair", "exit", "quit"):
            print("Encerrando agente.")
            break
        if not tarefa:
            continue
        agent.run(tarefa)


if __name__ == "__main__":
    main()
