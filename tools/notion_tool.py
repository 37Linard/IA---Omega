import logging
import os

log = logging.getLogger(__name__)


def _get_token():
    try:
        from config import NOTION_TOKEN
        return NOTION_TOKEN
    except ImportError:
        return ""


class NotionTool:
    name = "notion"
    description = (
        "Cria ou busca páginas no Notion. "
        "Input: {'action': 'create|search', 'title': 'Título', 'content': 'Texto', 'query': 'busca'}"
    )

    def run(self, input_data: dict) -> str:
        token = _get_token()
        if not token:
            return (
                "Notion não configurado. Adicione NOTION_TOKEN em config.py.\n"
                "Como obter: notion.so/my-integrations → criar integração → copiar token."
            )

        action = input_data.get("action", "create").lower()
        try:
            import requests
        except ImportError:
            return "Erro: requests não instalado."

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
            "Notion-Version": "2022-06-28",
        }

        if action == "search":
            query = input_data.get("query", "")
            r = requests.post(
                "https://api.notion.com/v1/search",
                headers=headers,
                json={"query": query, "page_size": 5},
                timeout=10,
            )
            if r.status_code != 200:
                return f"Erro Notion ({r.status_code}): {r.text[:200]}"
            results = r.json().get("results", [])
            if not results:
                return "Nenhuma página encontrada no Notion."
            lines = [f"Encontrado {len(results)} página(s):"]
            for p in results:
                title = ""
                props = p.get("properties", {})
                for v in props.values():
                    if v.get("type") == "title":
                        rich = v.get("title", [])
                        title = "".join(t.get("plain_text", "") for t in rich)
                        break
                lines.append(f"- {title or 'Sem título'} | {p.get('url', '')}")
            return "\n".join(lines)

        elif action == "create":
            try:
                from config import NOTION_DATABASE_ID
                db_id = NOTION_DATABASE_ID
            except ImportError:
                return "NOTION_DATABASE_ID não configurado em config.py."

            title   = input_data.get("title", "Nova página")
            content = input_data.get("content", "")

            body = {
                "parent": {"database_id": db_id},
                "properties": {
                    "Name": {"title": [{"text": {"content": title}}]}
                },
                "children": [
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": content[:2000]}}]
                        },
                    }
                ] if content else [],
            }
            r = requests.post(
                "https://api.notion.com/v1/pages",
                headers=headers,
                json=body,
                timeout=10,
            )
            if r.status_code not in (200, 201):
                return f"Erro Notion ({r.status_code}): {r.text[:200]}"
            url = r.json().get("url", "")
            return f"Página '{title}' criada no Notion: {url}"

        return f"Ação desconhecida: '{action}'. Use 'create' ou 'search'."
