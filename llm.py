import json
import logging
import time
import requests
import tracing
from config import OLLAMA_URL, NUM_PREDICT, NUM_CTX, NUM_GPU, TEMPERATURE, VISION_MODEL, KEEP_ALIVE, FALLBACK_MODEL

log = logging.getLogger(__name__)


def _trace(kind: str, model: str, t0: float, call_stats: dict = None, *,
           success: bool = True, error: str = "", fallback_used: bool = False,
           prompt_preview: str = ""):
    """Grava um span (tracing.py). Chamada por valor/retorno, nunca por atributo
    de instância — OllamaLLM é compartilhado entre threads (specialists paralelos
    no modo colaborativo), estado por-chamada em self vazaria entre elas."""
    call_stats = call_stats or {}
    tracing.record_span(
        kind=kind, model=model, duration_ms=(time.monotonic() - t0) * 1000,
        prompt_tokens=call_stats.get("prompt_tokens", 0),
        completion_tokens=call_stats.get("completion_tokens", 0),
        tps=call_stats.get("tps", 0.0),
        success=success, error=error, fallback_used=fallback_used,
        prompt_preview=prompt_preview,
    )

MAX_RETRIES = 3
RETRY_DELAY = 5  # segundos — dá tempo pro Ollama carregar o modelo


def unload_all_models():
    """Descarrega da VRAM todo modelo Ollama atualmente carregado (keep_alive=0).
    Usado antes de generate_image na GPU — RTX 2060 6GB não cabe Ollama + Stable
    Diffusion ao mesmo tempo (medido: ~156MB livres de 6GB, thrashing). O próximo
    request normal recarrega sozinho (KEEP_ALIVE), só adiciona latência na 1ª
    chamada depois da imagem."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/ps", timeout=5)
        loaded = [m["name"] for m in r.json().get("models", [])]
    except Exception as e:
        log.warning("Não consegui listar modelos carregados no Ollama (%s) — pulando unload", e)
        return
    for name in loaded:
        try:
            requests.post(f"{OLLAMA_URL}/api/generate",
                          json={"model": name, "prompt": "", "keep_alive": 0}, timeout=10)
            log.info("Ollama: descarregado %s da VRAM (liberando espaço pra generate_image)", name)
        except Exception as e:
            log.warning("Falha ao descarregar %s do Ollama (%s)", name, e)


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

    def _update_stats(self, data: dict) -> dict:
        """Atualiza session_tokens (agregado cumulativo, pro dashboard) e retorna
        as stats DESSA chamada isoladas (pro span) — os dois têm granularidade
        diferente de propósito."""
        eval_count    = data.get("eval_count", 0)
        eval_dur_ns   = data.get("eval_duration", 0)
        prompt_count  = data.get("prompt_eval_count", 0)
        prompt_dur_ns = data.get("prompt_eval_duration", 0)
        load_dur_ns   = data.get("load_duration", 0)

        self.session_tokens["prompt"]     += prompt_count
        self.session_tokens["completion"] += eval_count

        tps = 0.0
        if eval_dur_ns > 0 and eval_count > 0:
            tps = round(eval_count / (eval_dur_ns / 1e9), 1)
            self.session_tokens["tps"] = tps

        ttft_ns = load_dur_ns + prompt_dur_ns
        if ttft_ns > 0:
            self.session_tokens["ttft_ms"] = round(ttft_ns / 1e6, 0)

        if prompt_count > 0 and NUM_CTX > 0:
            self.session_tokens["context_pct"] = round(prompt_count / NUM_CTX * 100, 1)

        return {"prompt_tokens": prompt_count, "completion_tokens": eval_count, "tps": tps}

    def _request(self, model: str, prompt: str, options: dict, on_token) -> tuple[str, dict]:
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
            call_stats = self._update_stats(data)
            return data["response"].strip(), call_stats

        full_response = ""
        call_stats = {}
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
                    call_stats = self._update_stats(data)
                    break
        return full_response.strip(), call_stats

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

        t0 = time.monotonic()
        last_err = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                text, call_stats = self._request(self.model, prompt, options, on_token)
                _trace("generate", self.model, t0, call_stats, prompt_preview=prompt[:150])
                return text
            except (requests.Timeout, requests.ConnectionError) as e:
                last_err = e
                log.warning("LLM tentativa %d/%d falhou (%s): %s", attempt, MAX_RETRIES, self.model, e)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
            except requests.HTTPError as e:
                _trace("generate", self.model, t0, success=False, error=str(e), prompt_preview=prompt[:150])
                raise RuntimeError(f"Erro Ollama: {e}") from e

        if self.fallback_model and self.fallback_model != self.model:
            log.warning("LLM: '%s' indisponível após %d tentativas — usando fallback '%s'",
                        self.model, MAX_RETRIES, self.fallback_model)
            try:
                text, call_stats = self._request(self.fallback_model, prompt, options, on_token)
                _trace("generate", self.fallback_model, t0, call_stats, fallback_used=True, prompt_preview=prompt[:150])
                return text
            except Exception as fe:
                _trace("generate", self.fallback_model, t0, success=False, error=str(fe),
                       fallback_used=True, prompt_preview=prompt[:150])
                raise RuntimeError(
                    f"Ollama não respondeu ('{self.model}') e fallback '{self.fallback_model}' também falhou: {fe}"
                ) from fe

        _trace("generate", self.model, t0, success=False, error=str(last_err), prompt_preview=prompt[:150])
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
        vision_model = model or VISION_MODEL
        payload = {
            "model":      vision_model,
            "prompt":     prompt,
            "images":     [image_b64],
            "stream":     False,
            "keep_alive": KEEP_ALIVE,
            "options":    {"temperature": TEMPERATURE, "num_predict": NUM_PREDICT, "num_gpu": NUM_GPU},
        }
        t0 = time.monotonic()
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                r = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=120)
                r.raise_for_status()
                data = r.json()
                call_stats = self._update_stats(data)
                _trace("generate_vision", vision_model, t0, call_stats, prompt_preview=prompt[:150])
                return data["response"].strip()
            except (requests.Timeout, requests.ConnectionError) as e:
                log.warning("Vision LLM tentativa %d/%d: %s", attempt, MAX_RETRIES, e)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)
                else:
                    _trace("generate_vision", vision_model, t0, success=False, error=str(e), prompt_preview=prompt[:150])
                    raise RuntimeError(f"Ollama vision não respondeu após {MAX_RETRIES} tentativas.") from e
            except requests.HTTPError as e:
                _trace("generate_vision", vision_model, t0, success=False, error=str(e), prompt_preview=prompt[:150])
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
