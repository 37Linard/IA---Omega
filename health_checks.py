"""Checagens puras usadas pelo endpoint /health — sem imports pesados
(api.py importa voice/scheduler/watcher e sobe threads no import, então fica
inviável testar direto; isso aqui fica isolado e testável)."""


def jwt_secret_warning(auth_password: str, jwt_secret: str) -> str:
    """AUTH_PASSWORD protege a API só se o JWT também for forjável-resistente.
    Com JWT_SECRET vazio, jwt.encode assina com segredo "" — qualquer um monta
    um token válido sem saber a senha. Sem AUTH_PASSWORD não tem auth pra
    burlar, então não avisa (nada a proteger)."""
    if auth_password and not jwt_secret:
        return (
            "AUTH_PASSWORD configurada mas JWT_SECRET vazio — tokens JWT ficam "
            "forjáveis (assinados com segredo vazio). Defina JWT_SECRET via env var."
        )
    return ""


def remote_access_warning(auth_password: str) -> str:
    """`--host 0.0.0.0` (padrão dos .bat) já deixa a API alcançável por
    qualquer dispositivo na LAN ou tailnet (Tailscale) — não só localhost.
    Sem AUTH_PASSWORD, qualquer um nessa rede tem acesso total (terminal,
    arquivos, e-mail, etc. — tools "destructive" inteiras). Não tem como
    checar o bind real daqui dentro (uvicorn recebe --host fora do app),
    então avisa sempre que estiver vazia — melhor aviso de sobra numa
    instalação 100% localhost do que silêncio numa exposta de verdade."""
    if not auth_password:
        return (
            "AUTH_PASSWORD vazia — se você expõe essa API além de localhost "
            "(Tailscale, LAN), qualquer dispositivo nessa rede tem acesso total "
            "ao agente sem senha nenhuma. Configure AUTH_PASSWORD em config.py "
            "antes de acessar remoto."
        )
    return ""
