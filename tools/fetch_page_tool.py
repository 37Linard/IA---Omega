import requests
import re
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

from tools._security import wrap_untrusted


class FetchPageTool:
    name = "fetch_page"
    description = (
        "Acessa uma URL e extrai o texto legível da página. "
        "Use quando web_search retornar links mas não o dado em si. "
        "Input: {'url': 'https://...'}"
    )

    def run(self, input_data: dict) -> str:
        url = input_data.get("url", "")

        if not url:
            return "Erro: campo 'url' obrigatório."

        if not url.startswith("http"):
            return "Erro: URL deve começar com http:// ou https://"

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            if BS4_AVAILABLE:
                soup = BeautifulSoup(response.text, "html.parser")

                # Remove scripts, styles, nav, footer
                for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    tag.decompose()

                text = soup.get_text(separator="\n")
            else:
                # Fallback sem bs4 — remove tags com regex
                text = re.sub(r"<[^>]+>", " ", response.text)

            # Limpa linhas em branco excessivas
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            clean = "\n".join(lines)

            # Limita pra não explodir contexto do LLM
            if len(clean) > 4000:
                clean = clean[:4000] + "\n\n[... página truncada ...]"

            if not clean:
                return "Página sem conteúdo legível."
            return wrap_untrusted(url, clean)

        except requests.Timeout:
            return "Erro: página não respondeu em 15 segundos."
        except requests.HTTPError as e:
            return f"Erro HTTP {e.response.status_code}: {url}"
        except Exception as e:
            return f"Erro ao acessar página: {str(e)}"
