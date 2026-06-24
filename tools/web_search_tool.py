try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS


class WebSearchTool:
    name = "web_search"
    description = "Pesquisa na internet e retorna resultados relevantes. Input: {'query': 'sua pesquisa aqui'}"

    def run(self, input_data: dict) -> str:
        query = input_data.get("query", "")

        if not query:
            return "Erro: campo 'query' obrigatório."

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=4))

            if not results:
                return "Nenhum resultado encontrado."

            output = []
            for i, r in enumerate(results, 1):
                output.append(f"[{i}] {r['title']}")
                output.append(f"    URL: {r['href']}")
                output.append(f"    {r['body']}")
                output.append("")

            return "\n".join(output)

        except Exception as e:
            return f"Erro na pesquisa: {str(e)}"
