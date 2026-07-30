import os
from datetime import datetime


SAFE_DIR      = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workspace")
SNAPSHOT_DIR  = os.path.join(SAFE_DIR, ".file_snapshots")
MAX_SNAPSHOTS = 10  # por arquivo — mesmo espírito do MAX_BACKUPS do memory.py, evita crescer sem limite


def _snapshot_prefix(filename: str) -> str:
    return f"{filename}."


def _list_snapshots(filename: str) -> list[str]:
    """Timestamps (ordenados, mais antigo primeiro) dos snapshots existentes
    pra este filename — o formato %Y%m%dT%H%M%S%f ordena igual cronologicamente
    por string, não precisa parsear pra achar o mais recente."""
    if not os.path.isdir(SNAPSHOT_DIR):
        return []
    prefix = _snapshot_prefix(filename)
    hits = [f for f in os.listdir(SNAPSHOT_DIR) if f.startswith(prefix) and f.endswith(".bak")]
    return sorted(hits)


def _snapshot_path(filename: str, ts: str) -> str:
    return os.path.join(SNAPSHOT_DIR, f"{filename}.{ts}.bak")


def _save_snapshot(filename: str, content: str) -> str:
    """Grava o conteúdo ATUAL antes de sobrescrever/restaurar. Poda os mais
    antigos além de MAX_SNAPSHOTS — feito aqui (não como job separado) porque
    é rápido e cada write_file já é uma operação isolada, sem necessidade de
    um mecanismo de manutenção à parte como audit.prune()/kg.consolidate()."""
    os.makedirs(SNAPSHOT_DIR, exist_ok=True)
    # microssegundos -- achado real: %H%M%S sozinho colide em escritas
    # rápidas sucessivas (mesmo segundo = snapshot anterior sobrescrito,
    # perde histórico em vez de acumular)
    ts = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    path = _snapshot_path(filename, ts)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    existing = _list_snapshots(filename)
    for old in existing[:-MAX_SNAPSHOTS] if len(existing) > MAX_SNAPSHOTS else []:
        try:
            os.remove(os.path.join(SNAPSHOT_DIR, old))
        except OSError:
            pass
    return ts


class WriteFileTool:
    name = "write_file"
    description = (
        "Cria ou sobrescreve um arquivo com conteúdo. "
        "Só escreve dentro da pasta workspace segura. "
        "Sobrescrever tira um snapshot do conteúdo anterior automaticamente — "
        "dá pra desfazer com action='restore'. "
        "Input escrever: {'filename': 'nome.txt', 'content': 'conteúdo aqui'} "
        "Input desfazer: {'filename': 'nome.txt', 'action': 'restore'} (restaura o snapshot mais recente; "
        "aceita {'version': '<timestamp>'} pra restaurar um específico) "
        "Input listar versões: {'filename': 'nome.txt', 'action': 'list_snapshots'}"
    )

    def run(self, input_data: dict) -> str:
        filename = os.path.basename(input_data.get("filename", ""))
        action   = input_data.get("action", "write")

        if not filename:
            return "Erro: campo 'filename' obrigatório."
        if "." not in filename:
            return f"Erro: '{filename}' não tem extensão. Use ex: 'resultado.txt', 'dados.json'."

        os.makedirs(SAFE_DIR, exist_ok=True)
        safe_path = os.path.join(SAFE_DIR, filename)

        if action == "list_snapshots":
            snaps = _list_snapshots(filename)
            if not snaps:
                return f"Nenhum snapshot de '{filename}'."
            versions = [s[len(_snapshot_prefix(filename)):-len(".bak")] for s in snaps]
            return f"Snapshots de '{filename}' (mais antigo -> mais recente): {', '.join(versions)}"

        if action == "restore":
            version = input_data.get("version", "").strip()
            snaps = _list_snapshots(filename)
            if not snaps:
                return f"Erro: nenhum snapshot de '{filename}' pra restaurar."
            target = _snapshot_path(filename, version) if version else os.path.join(SNAPSHOT_DIR, snaps[-1])
            if not os.path.isfile(target):
                return f"Erro: versão '{version}' de '{filename}' não encontrada. Use action='list_snapshots'."
            try:
                with open(target, encoding="utf-8") as f:
                    restored_content = f.read()
                # snapshot do estado atual antes de restaurar -- restore tambem
                # e desfazivel, nao e uma via de mao unica
                if os.path.isfile(safe_path):
                    with open(safe_path, encoding="utf-8") as f:
                        _save_snapshot(filename, f.read())
                with open(safe_path, "w", encoding="utf-8") as f:
                    f.write(restored_content)
                return f"'{filename}' restaurado a partir do snapshot {os.path.basename(target)}."
            except Exception as e:
                return f"Erro ao restaurar: {str(e)}"

        # action == "write" (default)
        content = input_data.get("content", "")
        try:
            if os.path.isfile(safe_path):
                with open(safe_path, encoding="utf-8") as f:
                    _save_snapshot(filename, f.read())
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Arquivo criado: {safe_path}"
        except Exception as e:
            return f"Erro ao escrever arquivo: {str(e)}"
