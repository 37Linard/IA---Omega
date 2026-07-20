import json
import logging
import time
import requests
from config import OLLAMA_URL, NUM_PREDICT, NUM_CTX, NUM_GPU, TEMPERATURE, VISION_MODEL, KEEP_ALIVE, FALLBACK_MODEL

log = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 5  # segundos — dá tempo pro Ollama carregar o modelo


class OllamaLLM:
    def __init__(self, model: str = "qwen2.5:7b", fallback_model: str = None):
        self.model          = model
        self.base_url       = OLLAMA_URL
        self.fallback_model = FALLBACK_MODEL if fallback_model is None else fallback_model
        self.session_tokens = {
            "prompt": 0, "completion": 0,
            "tps": 0.0, "ttft_ms": 0.0, "context_pct": 0.0,
        }

    def reset_tokens(self):
        self.session_tokens = {
            "prompt": 0, "completion": 0,
            "tps": 0.0, "ttft_ms": 0.0, "context_pct": 0.0,
        }

    def _update_stats(self, data: dict):
        eval_count    = data.get("eval_count", 0)
        eval_dur_ns   = data.get("eval_duration", 0)
        prompt_count  = data.get("prompt_eval_count", 0)
        prompt_dur_ns = data.get("prompt_eval_duration", 0)
        load_dur_ns   = data.get("load_duration", 0)

        self.session_tokens["prompt"]     += prompt_count
        self.session_tokens["completion"] += eval_count

        if eval_dur_ns > 0 and eval_count > 0:
            self.session_tokens["tps"] = round(eval_count / (eval_dur_ns / 1e9), 1)

        ttft_ns = load_dur_ns + prompt_dur_ns
        if ttft_ns > 0:
            self.session_tokens["ttft_ms"] = round(ttft_ns / 1e6, 0)

        if prompt_count > 0 and NUM_CTX > 0:
            self.session_tokens["context_pct"] = round(prompt_count / NUM_CTX * 100, 1)

    def _request(self, model: str, prompt: str, options: dict, on_token) -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": on_token is not None,
            "keep_alive": KEEP_ALIVE,
            "options": options,
        }

        if on_token is None:
            response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=120)
            response.raise_for_status()
            data = response.json()
            self._update_stats(data)
            return data["response"].strip()

        full_response = ""
        with requests.post(f"{self.base_url}/api/generate", json=payload, stream=True, timeout=120) as response:
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
                    self._update_stats(data)
                    break
        return full_response.strip()

    def generate(self, prompt: str, on_token=None) -> str:
        """Gera resposta com retry automático; cai pro FALLBACK_MODEL se o modelo
        principal travar/timeout após esgotar as tentativas (em vez de falhar a tarefa)."""
        options = {
            "temperature": TEMPERATURE,
            "stop": ["Observation:", "Observação:", "\nObservation:", "\nObservação:"],
            "num_predict": NUM_PREDICT,
            "num_ctx": NUM_CTX,
            "num_gpu": NUM_GPU,
        }

        last_err = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return self._request(self.model, prompt, options, on_token)
            except (requests.Timeout, requests.ConnectionError) as e:
                last_err = e
                log.warning("LLM tentativa %d/%d falhou (%s): %s", attempt, MAX_RETRIES, self.model, e)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
            except requests.HTTPError as e:
                raise RuntimeError(f"Erro Ollama: {e}") from e

        if self.fallback_model and self.fallback_model != self.model:
            log.warning("LLM: '%s' indisponível após %d tentativas — usando fallback '%s'",
                        self.model, MAX_RETRIES, self.fallback_model)
            try:
                return self._request(self.fallback_model, prompt, options, on_token)
            except Exception as fe:
                raise RuntimeError(
                    f"Ollama não respondeu ('{self.model}') e fallback '{self.fallback_model}' também falhou: {fe}"
                ) from fe

        raise RuntimeError(f"Ollama não respondeu após {MAX_RETRIES} tentativas.") from last_err

    def embed(self, text: str) -> list[float]:
        """Generate embedding vector via Ollama (nomic-embed-text)."""
        from config import EMBED_MODEL
        r = requests.post(
            f"{self.base_url}/api/embeddings",
            json={"model": EMBED_MODEL, "prompt": text},
            timeout=30
        )
        r.raise_for_status()
        return r.json()["embedding"]

    def generate_vision(self, prompt: str, image_b64: str, model: str = "") -> str:
        """Analisa imagem com modelo multimodal."""
        payload = {
            "model":      model or VISION_MODEL,
            "prompt":     prompt,
            "images":     [image_b64],
            "stream":     False,
            "keep_alive": KEEP_ALIVE,
            "options":    {"temperature": TEMPERATURE, "num_predict": NUM_PREDICT, "num_gpu": NUM_GPU},
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


class OllamaEmbeddingFunction:
    """ChromaDB-compatible embedding function using Ollama (nomic-embed-text)."""

    def __init__(self, model: str, url: str):
        self.model = model
        self.url   = url

    def __call__(self, input: list[str]) -> list[list[float]]:
        # Ollama serializa embeddings (uma requisição por vez no motor) — testado:
        # 8 chamadas em paralelo enfileiram e algumas estouram timeout (30s),
        # voltando vetor zero e corrompendo o índice silenciosamente. Sequencial
        # é o comportamento seguro aqui.
        embeddings = []
        for text in input:
            try:
                r = requests.post(
                    f"{self.url}/api/embeddings",
                    json={"model": self.model, "prompt": text},
                    timeout=30
                )
                r.raise_for_status()
                embeddings.append(r.json()["embedding"])
            except Exception as e:
                log.warning("OllamaEmbeddingFunction: %s", e)
                embeddings.append([0.0] * 768)
        return embeddings

    @staticmethod
    def is_available(model: str, url: str) -> bool:
        try:
            r = requests.post(
                f"{url}/api/embeddings",
                json={"model": model, "prompt": "test"},
                timeout=5
            )
            return r.status_code == 200 and "embedding" in r.json()
        except Exception:
            return False
