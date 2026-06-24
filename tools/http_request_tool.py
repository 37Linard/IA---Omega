import requests
import json


class HttpRequestTool:
    name = "http_request"
    description = (
        "Faz requisições HTTP GET ou POST para APIs. "
        "Input: {'url': 'https://...', 'method': 'GET', 'headers': {}, 'body': {}}"
    )

    def run(self, input_data: dict) -> str:
        url     = input_data.get("url", "")
        method  = input_data.get("method", "GET").upper()
        headers = input_data.get("headers", {})
        body    = input_data.get("body", {})

        if not url:
            return "Erro: campo 'url' obrigatório."

        if not url.startswith("http"):
            return "Erro: URL deve começar com http:// ou https://"

        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=15)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=body, timeout=15)
            else:
                return f"Erro: método '{method}' não suportado. Use GET ou POST."

            # Tenta retornar JSON formatado, senão retorna texto
            try:
                data = response.json()
                result = json.dumps(data, indent=2, ensure_ascii=False)
            except Exception:
                result = response.text

            # Limita resposta pra não explodir contexto do LLM
            if len(result) > 3000:
                result = result[:3000] + "\n\n[... resposta truncada ...]"

            return f"Status: {response.status_code}\n\n{result}"

        except requests.Timeout:
            return "Erro: requisição excedeu 15 segundos."
        except Exception as e:
            return f"Erro na requisição: {str(e)}"
