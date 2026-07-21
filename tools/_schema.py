"""
Helper compartilhado — sem sufixo _tool.py de propósito, tool_loader.py ignora.

Validação RASA de propósito: só pega campo obrigatório faltando e valor de enum
inválido, ANTES de gastar tempo executando a tool (rede, subprocess, browser) ou
— pior — disparar HITL (agent.py) pedindo aprovação humana pra uma chamada que já
tá condenada a falhar por input malformado. Cada tool continua dona da própria
validação de tipo/semântica; isso não substitui os checks internos, só evita o
caso mais barato e mais comum de pegar cedo (modelo local pequeno esquece campo
ou inventa valor de enum).

Formato de TOOL_SCHEMAS[tool]:
  required:          lista de campos obrigatórios. Um item pode ser uma tupla
                      ("a", "b") pra dizer "pelo menos um desses dois".
  enum:              {campo: [valores válidos]}
  required_by_action: {valor_de_action: [campos extras obrigatórios nesse ramo]}
                      — só usado quando o próprio tool não tem default seguro
                      pra 'action' (branch teria que existir pra validar).
"""

TOOL_SCHEMAS = {
    "remember_fact":    {"required": ["fact"]},
    "save_note":        {"required": ["title", "content"]},
    "http_request":     {"required": ["url"]},
    "read_file":        {"required": ["path"]},
    "list_directory":   {"required": ["path"]},
    "clipboard":        {"required": [], "required_by_action": {"write": ["text"]}},
    "git": {
        "required": ["repo", "command"],
        "enum": {"command": ["add", "branch", "commit", "diff", "fetch", "log", "show", "stash", "status", "tag"]},
    },
    "terminal":         {"required": ["command"]},
    "send_email":       {"required": ["to", "subject"]},
    "analyze_image":    {"required": ["path"]},
    "read_spreadsheet": {"required": ["path"]},
    "slack":            {"required": [], "required_by_action": {"send": ["message"]}},
    "run_sql":          {"required": ["db", "query"]},
    "write_file":       {"required": ["filename"]},
    "run_python":       {"required": ["code"]},
    "generate_chart":   {"required": ["values"]},
    "generate_image":   {"required": [("prompt", "description")]},
    "discord_notify":   {"required": ["message"]},
    "fetch_page":       {"required": ["url"]},
    "web_search":       {"required": ["query"]},
    "rag_search":       {"required": ["query"]},
    "browser": {
        "required": ["action"],
        "enum": {"action": ["visual_goto", "visual_describe", "goto", "click", "type",
                             "scroll", "get_text", "screenshot"]},
        "required_by_action": {"visual_goto": ["url"], "goto": ["url"]},
    },
    "google_drive": {
        "required": ["action"],
        "enum": {"action": ["list", "read", "create", "update"]},
        "required_by_action": {"read": ["file_id"], "update": ["file_id"]},
    },
    "schedule_task": {
        "required": ["action"],
        "enum": {"action": ["create", "list", "remove"]},
        "required_by_action": {"create": ["task", "hour"], "remove": ["id"]},
    },
}


def _present(action_input: dict, field: str) -> bool:
    return bool(str(action_input.get(field, "")).strip())


def validate(tool_name: str, action_input) -> str:
    """Retorna mensagem de erro (str) se action_input não bate com o schema
    conhecido de tool_name, ou "" se passou (ou se a tool não tem schema)."""
    schema = TOOL_SCHEMAS.get(tool_name)
    if not schema or not isinstance(action_input, dict):
        return ""

    for field in schema.get("required", []):
        if isinstance(field, (tuple, list)):
            if not any(_present(action_input, f) for f in field):
                return f"Erro: obrigatório um destes campos para '{tool_name}': {list(field)}."
        elif not _present(action_input, field):
            return f"Erro: campo '{field}' obrigatório para '{tool_name}'."

    for field, allowed in schema.get("enum", {}).items():
        value = action_input.get(field)
        if value is not None and value not in allowed:
            return f"Erro: '{field}'={value!r} inválido para '{tool_name}'. Use um de: {allowed}."

    required_by_action = schema.get("required_by_action", {})
    if required_by_action:
        branch = action_input.get("action")
        for field in required_by_action.get(branch, []):
            if not _present(action_input, field):
                return f"Erro: campo '{field}' obrigatório para '{tool_name}' com action='{branch}'."

    return ""
