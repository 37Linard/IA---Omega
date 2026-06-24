import json
import requests


class OllamaLLM:
    def __init__(self, model: str = "llama3.2:3b"):
        self.model = model
        self.base_url = "http://localhost:11434"

    def generate(self, prompt: str, on_token=None) -> str:
        """Gera resposta. Se on_token fornecido, faz streaming token a token."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": on_token is not None,
            "options": {
                "temperature": 0.1,
                "stop": ["Observation:"],
                "num_predict": 500
            }
        }

        if on_token is None:
            # Sem streaming — retorna tudo de uma vez
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            return response.json()["response"].strip()

        # Com streaming — chama on_token pra cada token gerado
        full_response = ""
        with requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            stream=True,
            timeout=120
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                token = data.get("response", "")
                if token:
                    full_response += token
                    on_token(token)

                if data.get("done"):
                    break

        return full_response.strip()
