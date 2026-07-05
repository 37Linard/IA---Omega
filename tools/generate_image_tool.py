import os
import re
import sys
import time
import threading
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

log = logging.getLogger(__name__)

WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")

_pipeline = None
_pipeline_device = None
_pipeline_lock = threading.Lock()


def _get_pipeline():
    """Carrega o pipeline de geração de imagem uma única vez (lazy singleton).
    Tenta CUDA primeiro (GPU já é disputada com o Ollama — pode faltar VRAM),
    cai pra CPU automaticamente se a GPU não estiver disponível ou falhar.
    """
    global _pipeline, _pipeline_device
    if _pipeline is not None:
        return _pipeline, _pipeline_device

    with _pipeline_lock:
        if _pipeline is not None:
            return _pipeline, _pipeline_device

        from config import IMAGE_GEN_MODEL, IMAGE_GEN_DEVICE
        import torch
        from diffusers import AutoPipelineForText2Image

        if IMAGE_GEN_DEVICE in ("auto", "cuda") and torch.cuda.is_available():
            try:
                pipe = AutoPipelineForText2Image.from_pretrained(
                    IMAGE_GEN_MODEL, torch_dtype=torch.float16, safety_checker=None,
                )
                pipe = pipe.to("cuda")
                pipe.enable_attention_slicing()
                _pipeline, _pipeline_device = pipe, "cuda"
                log.info("Modelo de imagem carregado na GPU: %s", IMAGE_GEN_MODEL)
            except Exception as e:
                log.warning("Falha ao carregar modelo de imagem na GPU (%s) — usando CPU", e)

        if _pipeline is None:
            pipe = AutoPipelineForText2Image.from_pretrained(
                IMAGE_GEN_MODEL, torch_dtype=torch.float32, safety_checker=None,
            )
            pipe = pipe.to("cpu")
            _pipeline, _pipeline_device = pipe, "cpu"
            log.info("Modelo de imagem carregado na CPU: %s", IMAGE_GEN_MODEL)

    return _pipeline, _pipeline_device


class GenerateImageTool:
    name = "generate_image"
    description = (
        "Gera uma imagem a partir de uma descrição em texto, usando Stable Diffusion "
        "local (sem depender de API externa). Pode demorar — GPU: alguns segundos, "
        "CPU: 1-3 minutos, mais o tempo de carregar o modelo na 1ª chamada. "
        'Input: {"prompt": "descrição do que a imagem deve conter"}. '
        'IMPORTANTE: use so o conteudo pedido pelo usuario no prompt — NAO acrescente '
        'estilo tipo "arte digital"/"pintura"/"ilustracao" por conta propria, isso faz '
        'toda imagem sair parecendo pintura mesmo quando o usuario queria algo realista. '
        'So inclua estilo se o usuario pedir um explicitamente (ex: "estilo aquarela", "foto realista"). '
        'Campos opcionais: "output" (nome do arquivo, padrão gerado por timestamp), '
        '"negative_prompt", "steps" (1-8), "width"/"height" (padrão 512).'
    )

    def run(self, params: dict) -> str:
        # alguns modelos mandam "description" em vez de "prompt" — aceita os dois
        prompt = (params.get("prompt") or params.get("description") or "").strip()
        if not prompt:
            return "Erro: forneça 'prompt' com a descrição da imagem."

        negative_prompt = params.get("negative_prompt", "").strip() or None

        output = params.get("output", "").strip() or f"generated_{int(time.time())}.png"
        safe_output = os.path.basename(output)
        if not re.match(r'^[\w\-]+\.(png|jpg|jpeg)$', safe_output):
            safe_output = re.sub(r'[^\w\-.]', '_', safe_output)
            if not safe_output.lower().endswith((".png", ".jpg", ".jpeg")):
                safe_output += ".png"

        from config import IMAGE_GEN_STEPS, IMAGE_GEN_SIZE, IMAGE_GEN_GUIDANCE_SCALE

        try:
            steps = max(1, min(int(params.get("steps", IMAGE_GEN_STEPS)), 8))
        except (TypeError, ValueError):
            steps = IMAGE_GEN_STEPS
        try:
            width = int(params.get("width", IMAGE_GEN_SIZE))
            height = int(params.get("height", IMAGE_GEN_SIZE))
        except (TypeError, ValueError):
            width = height = IMAGE_GEN_SIZE

        try:
            pipe, device = _get_pipeline()
        except Exception as e:
            return (
                f"Erro: modelo de geração de imagem indisponível ({e}). "
                "Instale as dependências: pip install torch diffusers accelerate"
            )

        try:
            kwargs = dict(
                prompt=prompt,
                num_inference_steps=steps,
                width=width,
                height=height,
                guidance_scale=IMAGE_GEN_GUIDANCE_SCALE,
            )
            if negative_prompt:
                kwargs["negative_prompt"] = negative_prompt

            result = pipe(**kwargs)
            image = result.images[0]

            os.makedirs(WORKSPACE_DIR, exist_ok=True)
            filepath = os.path.join(WORKSPACE_DIR, safe_output)
            image.save(filepath)
        except Exception as e:
            return f"Erro ao gerar imagem: {e}"

        try:
            from tools.browser_tool import _img_url
            url = _img_url(safe_output)
        except Exception:
            from config import API_URL
            url = f"{API_URL}/workspace/img/{safe_output}"

        log.info("Imagem gerada (%s): %s", device, filepath)
        return f"Imagem gerada ({device}) e salva em workspace/{safe_output}.\n![{prompt}]({url})"
