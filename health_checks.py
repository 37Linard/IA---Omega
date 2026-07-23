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
