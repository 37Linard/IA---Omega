import ast
import os

import pytest

_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PY = os.path.join(_PROJECT, "config.py")
CONFIG_EXAMPLE_PY = os.path.join(_PROJECT, "config.example.py")


def _top_level_names(path: str) -> set[str]:
    """Nomes definidos no nivel do modulo (variaveis + funcoes), via AST -
    nao importa o arquivo, entao nao precisa dos segredos reais serem
    validos nem executa nada (config.py tem valor de webhook/senha real)."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)

    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                names.update(_assign_target_names(target))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
    return names


def _assign_target_names(target: ast.expr) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        out: set[str] = set()
        for elt in target.elts:
            out.update(_assign_target_names(elt))
        return out
    return set()


def test_config_example_has_no_drift_from_real_config():
    """config.example.py e o template que qualquer clone novo copia pra
    config.py (README manda `cp config.example.py config.py`). Se
    config.py real ganha um nome que o template nao tem, esse fluxo
    quebra com ImportError pra quem clonar do zero - ja aconteceu 2x em
    producao (KEEP_ALIVE sozinho, depois mais 10 nomes de uma vez -
    API_URL/EMBED_MODEL/MANAGER_MODEL/REDIS_URL/REFLECTION_ENABLED/
    REFLECTION_THRESHOLD/SHORT_TERM_MSGS/SHORT_TERM_TTL/SPECIALIST_MODELS/
    link_note_in_conversas_index -, achados ao vivo rodando o CI, nao por
    teste nenhum ate agora). Este teste pega o drift antes de virar bug.
    """
    if not os.path.isfile(CONFIG_PY):
        pytest.skip("config.py nao existe neste ambiente (nada pra comparar)")

    real_names = _top_level_names(CONFIG_PY)
    example_names = _top_level_names(CONFIG_EXAMPLE_PY)

    missing_from_example = real_names - example_names
    assert not missing_from_example, (
        f"config.py tem {len(missing_from_example)} nome(s) que config.example.py "
        f"nao tem: {sorted(missing_from_example)}. Clone novo seguindo "
        "'cp config.example.py config.py' vai quebrar com ImportError. "
        "Adicione em config.example.py (documentado, sem o valor real)."
    )
