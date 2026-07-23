import base64
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import ALLOWED_READ_DIRS, VISION_MODEL
from tools._paths import is_allowed_path

SUPPORTED_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}


class AnalyzeImageTool:
    name = "analyze_image"
    description = (
        "Analisa uma imagem usando modelo de visão (LLaVA). "
        "Descreve conteúdo, lê texto, identifica objetos, responde perguntas sobre a imagem. "
        'Input: {"path": "workspace/foto.png", "prompt": "O que há nesta imagem?"} '
        'O campo "prompt" é opcional — padrão: descreva a imagem.'
    )

    def run(self, params: dict) -> str:
        path   = params.get("path", "").strip()
        prompt = params.get("prompt", "Descreva detalhadamente o que você vê nesta imagem.").strip()

        if not path:
            return "Erro: forneça 'path' da imagem."

        # Resolve path relativo ao workspace
        if not os.path.isabs(path):
            workspace = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
            path = os.path.join(workspace, path)

        path = os.path.normpath(path)

        # Whitelist
        workspace_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
        allowed = is_allowed_path(path, list(ALLOWED_READ_DIRS) + [workspace_dir])
        if not allowed:
            return f"Erro: caminho não permitido — '{path}'."

        if not os.path.isfile(path):
            return f"Erro: arquivo não encontrado — '{path}'."

        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_EXT:
            return f"Erro: formato não suportado. Use: {', '.join(SUPPORTED_EXT)}"

        try:
            with open(path, "rb") as f:
                image_b64 = base64.b64encode(f.read()).decode()
        except Exception as e:
            return f"Erro ao ler imagem: {e}"

        try:
            from llm import OllamaLLM
            llm    = OllamaLLM()
            result = llm.generate_vision(prompt, image_b64, model=VISION_MODEL)
            return f"[Análise de {os.path.basename(path)} com {VISION_MODEL}]\n\n{result}"
        except Exception as e:
            return f"Erro ao analisar imagem: {e}"
