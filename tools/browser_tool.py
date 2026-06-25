class BrowserTool:
    name = "browser"
    description = (
        "Controla Chrome via Playwright. Ações: goto, click, type, screenshot, get_text. "
        "Input: {'action': 'goto', 'url': 'https://...'} "
        "ou {'action': 'click', 'selector': '#btn'} "
        "ou {'action': 'type', 'selector': '#input', 'text': 'hello'} "
        "ou {'action': 'get_text', 'selector': 'body'} "
        "ou {'action': 'screenshot'}"
    )

    def __init__(self):
        self._browser = None
        self._page    = None

    def _ensure_browser(self):
        if self._browser is None:
            from playwright.sync_api import sync_playwright
            self._pw      = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=False)
            self._page    = self._browser.new_page()

    def run(self, input_data: dict) -> str:
        try:
            from playwright.sync_api import sync_playwright  # noqa: F401
        except ImportError:
            return "Erro: instale playwright — pip install playwright && playwright install chromium"

        action = input_data.get("action", "")
        try:
            self._ensure_browser()
            page = self._page

            if action == "goto":
                url = input_data.get("url", "")
                if not url.startswith("http"):
                    return "Erro: URL deve começar com http."
                page.goto(url, timeout=15000)
                return f"Navegou para: {url} — título: {page.title()}"

            elif action == "click":
                sel = input_data.get("selector", "")
                page.click(sel, timeout=5000)
                return f"Clicou em: {sel}"

            elif action == "type":
                sel  = input_data.get("selector", "")
                text = input_data.get("text", "")
                page.fill(sel, text)
                return f"Digitou em {sel}: {text[:50]}"

            elif action == "get_text":
                sel  = input_data.get("selector", "body")
                text = page.inner_text(sel)
                return text[:2000] if text else "Sem texto."

            elif action == "screenshot":
                import os, tempfile
                path = os.path.join(
                    r"C:\Users\User\Desktop\MEU\IA\workspace",
                    f"browser_shot.png"
                )
                os.makedirs(os.path.dirname(path), exist_ok=True)
                page.screenshot(path=path)
                return f"Screenshot salvo: {path}"

            else:
                return f"Ação '{action}' inválida. Use: goto, click, type, get_text, screenshot."

        except Exception as e:
            return f"Erro: {str(e)}"
