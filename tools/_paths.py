"""Checagem de path dentro de pastas permitidas — compartilhada entre
read_file/list_directory/read_spreadsheet/analyze_image (sem sufixo _tool.py
de propósito, tool_loader ignora, igual _security.py/_schema.py)."""
import os


def is_allowed_path(path: str, allowed_dirs: list[str]) -> bool:
    """startswith() puro tem bug de fronteira: "Desktop-secret/x" passa como
    se fosse dentro de "Desktop/" porque a string bate por prefixo sem checar
    separador. Achado 2026-07-23, duplicado em 4 tools antes dessa extração."""
    real = os.path.realpath(path)
    for d in allowed_dirs:
        real_d = os.path.realpath(d)
        if real == real_d or real.startswith(real_d + os.sep):
            return True
    return False
