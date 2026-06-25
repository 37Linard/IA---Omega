import json
import logging
import time
import requests
from config import OLLAMA_URL, NUM_PREDICT, NUM_CTX, NUM_GPU, TEMPERATURE, VISION_MODEL

log = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 5  # segundos — dá tempo pro Ollama carregar o modelo


class OllamaLLM:
    def __init__(self, model: str = "qwen2.5:7b"):
        self.model          = model
        self.base_url       = OLLAMA_URL
        self.session_tokens = {"prompt": 0, "completion": 0}

    def reset_tokens(self):
        self.session_tokens = {"prompt": 0, "completion": 0}

    def generate(self, prompt: str, on_token=None) -> str:
        """Gera resposta com retry automático em caso de falha."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": on_token is not None,
            "options": {
                "temperature": TEMPERATURE,
                "stop": ["Observation:"],
                "num_predict": NUM_PREDICT,
                "num_ctx": NUM_CTX,
                "num_gpu": NUM_GPU,
            }
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if on_token is None:
                    response = requests.post(
                        f"{self.base_url}/api/generate",
                        json=payload,
                        timeout=120
                    )
                    response.raise_for_status()
                    data = response.json()
                    self.session_tokens["prompt"]     += data.get("prompt_eval_count", 0)
                    self.session_tokens["completion"] += data.get("eval_count", 0)
                    return data["response"].strip()

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
                            self.session_tokens["prompt"]     += data.get("prompt_eval_count", 0)
                            self.session_tokens["completion"] += data.get("eval_count", 0)
                            break
                return full_response.strip()

            except (requests.Timeout, requests.ConnectionError) as e:
                log.warning("LLM tentativa %d/%d falhou: %s", attempt, MAX_RETRIES, e)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                else:
                    raise RuntimeError(f"Ollama não respondeu após {MAX_RETRIES} tentativas.") from e
            except requests.HTTPError as e:
                raise RuntimeError(f"Erro Ollama: {e}") from e

    def generate_vision(self, prompt: str, image_b64: str, model: str = "") -> str:
        """Analisa imagem com modelo multimodal."""
        payload = {
            "model":   model or VISION_MODEL,
            "prompt":  prompt,
            "images":  [image_b64],
            "stream":  False,
            "options": {"temperature": TEMPERATURE, "num_predict": NUM_PREDICT, "num_gpu": NUM_GPU},
        }
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                r = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=120)
                r.raise_for_status()
                return r.json()["response"].strip()
            except (requests.Timeout, requests.ConnectionError) as e:
                log.warning("Vision LLM tentativa %d/%d: %s", attempt, MAX_RETRIES, e)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                else:
                    raise RuntimeError(f"Ollama vision não respondeu após {MAX_RETRIES} tentativas.") from e
            except requests.HTTPError as e:
                raise RuntimeError(f"Erro Ollama vision: {e}") from e
