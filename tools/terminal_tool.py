import subprocess
import shlex

# Comandos permitidos — whitelist explícita
ALLOWED = {
    "dir", "ls", "echo", "type", "cat", "where", "which",
    "ping", "ipconfig", "date", "time", "tasklist",
    "python", "pip", "git", "node", "npm",
    "ollama", "curl", "wget",
}

BLOCKED_PATTERNS = [
    "rm ", "del ", "format ", "shutdown", "reboot",
    "reg ", "regedit", "netsh", "powershell -enc",
    "> c:\\windows", "> c:\\system",
]

# shell=True roda a string inteira, não só o 1º comando — sem isso a whitelist
# só filtra a "primeira palavra" e "echo oi && del /f /q C:\..." passava reto
# (achado real, 0 cobertura de teste). Nenhum uso legítimo dos comandos em
# ALLOWED precisa de encadeamento/pipe/redirecionamento.
SHELL_METACHARS = ["&", "|", ";", "`", "$(", ">", "<", "\n", "\r"]


def _is_safe(cmd: str) -> tuple[bool, str]:
    for meta in SHELL_METACHARS:
        if meta in cmd:
            return False, f"Caractere de encadeamento/redirecionamento não permitido: '{meta}'"
    lower = cmd.lower().strip()
    for pat in BLOCKED_PATTERNS:
        if pat in lower:
            return False, f"Padrão bloqueado: '{pat}'"
    first_word = lower.split()[0].split("\\")[-1].split("/")[-1]
    if first_word not in ALLOWED:
        return False, f"Comando '{first_word}' não permitido. Permitidos: {sorted(ALLOWED)}"
    return True, ""


class TerminalTool:
    name = "terminal"
    description = (
        "Executa comandos no terminal (sandboxed). "
        "Permitidos: dir, ls, echo, type, ping, ipconfig, tasklist, python, pip, git, ollama, etc. "
        "Input: {'command': 'dir C:\\Users\\User\\Desktop'}"
    )

    def run(self, input_data: dict) -> str:
        command = input_data.get("command", "").strip()
        if not command:
            return "Erro: campo 'command' obrigatório."

        ok, reason = _is_safe(command)
        if not ok:
            return f"Bloqueado: {reason}"

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=20,
                encoding="utf-8",
                errors="replace"
            )
            output = (result.stdout + result.stderr).strip()
            if len(output) > 2000:
                output = output[:2000] + "\n[... truncado ...]"
            return output or "Comando executado sem saída."
        except subprocess.TimeoutExpired:
            return "Erro: comando excedeu 20 segundos."
        except Exception as e:
            return f"Erro: {str(e)}"
