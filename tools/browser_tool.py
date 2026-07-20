"""
BrowserTool — Playwright + pipeline visual (screenshot → VLM).
Prefer visual_goto / visual_describe for understanding page content.
"""
import base64
import os
from datetime import datetime

from tools._security import wrap_untrusted

_PROJECT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE = os.path.join(_PROJECT, "workspace")


def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _take_screenshot(page, fname: str) -> str:
    os.makedirs(WORKSPACE, exist_ok=True)
    path = os.path.join(WORKSPACE, fname)
    page.screenshot(path=path)
    return path


def _vlm_analyze(path: str, prompt: str) -> str:
    try:
        from config import VISION_MODEL
        from llm import OllamaLLM
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        llm = OllamaLLM()
        return llm.generate_vision(prompt, b64, model=VISION_MODEL)
    except Exception as e:
        return f"[VLM indisponivel: {e}]"


def _img_url(fname: str) -> str:
    try:
        from config import API_URL
        return f"{API_URL}/workspace/img/{fname}"
    except Exception:
        return f"http://localhost:8000/workspace/img/{fname}"


class BrowserTool:
    name = "browser"
    description = (
        "Controla Chrome via Playwright com pipeline visual (screenshot + VLM). "
        "PREFERIR visual_goto para entender paginas — navega, captura screenshot, analisa com VLM. "
        "Acoes disponiveis: "
        "visual_goto: navega + screenshot + analise VLM. Input: {'action':'visual_goto','url':'https://...','prompt':'o que contem?'} "
        "visual_describe: screenshot pagina atual + analise VLM. Input: {'action':'visual_describe','prompt':'descreva'} "
        "goto: navega sem analise. Input: {'action':'goto','url':'https://...'} "
        "click: clica seletor CSS. Input: {'action':'click','selector':'#btn'} "
        "type: digita em campo. Input: {'action':'type','selector':'#input','text':'hello'} "
        "scroll: rola pagina. Input: {'action':'scroll','direction':'down','amount':500} "
        "get_text: extrai texto HTML. Input: {'action':'get_text','selector':'body'} "
        "screenshot: captura sem VLM. Input: {'action':'screenshot'}"
    )

    def __init__(self):
        self._browser = None
        self._page    = None

    def _ensure_browser(self):
        if self._browser is None:
            from playwright.sync_api import sync_playwright
            self._pw      = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True)
            self._page    = self._browser.new_page(
                viewport={"width": 1280, "height": 800}
            )

    def run(self, input_data: dict) -> str:
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except ImportError:
            return "Erro: instale playwright — pip install playwright && playwright install chromium"

        action = input_data.get("action", "")
        try:
            self._ensure_browser()
            page = self._page

            # ── Visual goto: navigate + screenshot + VLM ──────────────────
            if action == "visual_goto":
                url    = input_data.get("url", "")
                prompt = input_data.get(
                    "prompt",
                    "Descreva detalhadamente o conteudo desta pagina web: "
                    "textos principais, titulos, links, botoes, formularios, imagens e estrutura geral."
                )
                if not url.startswith("http"):
                    return "Erro: URL deve comecar com http."
                page.goto(url, timeout=20000, wait_until="domcontentloaded")
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass
                fname = f"browser_{_ts()}.png"
                path  = _take_screenshot(page, fname)
                desc  = _vlm_analyze(path, prompt)
                return (
                    f"URL: {url}\nTitulo: {page.title()}\n\n"
                    f"![screenshot]({_img_url(fname)})\n\n"
                    f"**Analise Visual:**\n{wrap_untrusted(url, desc)}"
                )

            # ── Visual describe: screenshot current state + VLM ────────────
            elif action == "visual_describe":
                prompt = input_data.get(
                    "prompt",
                    "Descreva detalhadamente o que esta visivel nesta pagina: "
                    "textos, botoes, formularios, imagens e estrutura."
                )
                fname = f"browser_{_ts()}.png"
                path  = _take_screenshot(page, fname)
                desc  = _vlm_analyze(path, prompt)
                return (
                    f"URL atual: {page.url}\nTitulo: {page.title()}\n\n"
                    f"![screenshot]({_img_url(fname)})\n\n"
                    f"**Analise Visual:**\n{wrap_untrusted(page.url, desc)}"
                )

            # ── Goto (sem VLM) ─────────────────────────────────────────────
            elif action == "goto":
                url = input_data.get("url", "")
                if not url.startswith("http"):
                    return "Erro: URL deve comecar com http."
                page.goto(url, timeout=20000, wait_until="domcontentloaded")
                return f"Navegou para: {url} — titulo: {page.title()}"

            # ── Click ──────────────────────────────────────────────────────
            elif action == "click":
                sel = input_data.get("selector", "")
                page.click(sel, timeout=5000)
                return f"Clicou em: {sel}"

            # ── Type ───────────────────────────────────────────────────────
            elif action == "type":
                sel  = input_data.get("selector", "")
                text = input_data.get("text", "")
                page.fill(sel, text)
                return f"Digitou em {sel}: {text[:50]}"

            # ── Scroll ─────────────────────────────────────────────────────
            elif action == "scroll":
                direction = input_data.get("direction", "down")
                amount    = int(input_data.get("amount", 500))
                delta = amount if direction == "down" else -amount
                page.mouse.wheel(0, delta)
                return f"Rolou {direction} {abs(amount)}px"

            # ── Get text ───────────────────────────────────────────────────
            elif action == "get_text":
                sel  = input_data.get("selector", "body")
                text = page.inner_text(sel)
                if not text:
                    return "Sem texto."
                return wrap_untrusted(page.url, text[:3000])

            # ── Screenshot only ────────────────────────────────────────────
            elif action == "screenshot":
                fname = f"browser_{_ts()}.png"
                _take_screenshot(page, fname)
                return f"Screenshot salvo.\n![screenshot]({_img_url(fname)})"

            else:
                return (
                    f"Acao '{action}' invalida. "
                    "Use: visual_goto, visual_describe, goto, click, type, scroll, get_text, screenshot."
                )

        except Exception as e:
            return f"Erro browser: {str(e)}"
