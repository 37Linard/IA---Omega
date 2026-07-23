import shlex
import subprocess
import os

ALLOWED_SUBCOMMANDS = {
    "status", "log", "diff", "branch", "show",
    "add", "commit", "stash", "tag", "fetch"
}
BLOCKED_LONG_FLAGS = {"--force", "--hard", "--no-verify", "--no-gpg-sign"}
# flags curtas combinadas (ex.: "git branch -Df") bypassavam o check antigo de
# substring ("-f" in "-Df" é False) — achado real, 0 cobertura de teste.
BLOCKED_SHORT_CHARS = {"f"}  # letra de "-f"/"--force"


class GitTool:
    name = "git"
    description = (
        "Executa comandos git em repositórios locais. "
        "Permite: status, log, diff, branch, show, add, commit, stash, tag, fetch. "
        "Input: {'repo': 'C:/caminho/repo', 'command': 'status'} "
        "ou {'repo': '...', 'command': 'commit', 'args': '-m \"mensagem\"'}"
    )

    def run(self, input_data: dict) -> str:
        repo    = input_data.get("repo", "").strip()
        command = input_data.get("command", "").strip().lower()
        args    = input_data.get("args", "").strip()

        if not repo:
            return "Erro: campo 'repo' obrigatório."
        if not os.path.isdir(repo):
            return f"Erro: '{repo}' não é um diretório."
        if command not in ALLOWED_SUBCOMMANDS:
            return f"Bloqueado: '{command}' não permitido. Permitidos: {sorted(ALLOWED_SUBCOMMANDS)}"

        try:
            tokens = shlex.split(args) if args else []
        except ValueError as e:
            return f"Erro: args inválido ({e})"

        for token in tokens:
            if token in BLOCKED_LONG_FLAGS:
                return f"Bloqueado: flag '{token}' não permitida."
            if token.startswith("-") and not token.startswith("--"):
                hit = BLOCKED_SHORT_CHARS & set(token[1:])
                if hit:
                    return f"Bloqueado: flag '-{hit.pop()}' não permitida (em '{token}')."

        cmd = ["git", command] + tokens
        try:
            result = subprocess.run(
                cmd, cwd=repo, capture_output=True, text=True, timeout=30
            )
            output = (result.stdout + result.stderr).strip()
            if len(output) > 2000:
                output = output[:2000] + "\n[... truncado ...]"
            return output or "Comando executado sem saída."
        except subprocess.TimeoutExpired:
            return "Erro: git excedeu 30 segundos."
        except Exception as e:
            return f"Erro: {str(e)}"
