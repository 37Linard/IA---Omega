"""
Plugin manager — mecanismo pra instalar ferramentas de terceiros via URL,
com verificação de integridade e execução sandboxada. Escopo desta versão:
design + sandboxing. NÃO existe instalação automática nem exposição como
tool do agente — tudo aqui é operado manualmente, por você.

MODELO DE SEGURANÇA (leia antes de habilitar):

  1. Instalar um plugin é SEMPRE uma ação manual do operador (você, rodando
     este script na linha de comando) — nunca algo que o agente decide
     sozinho em runtime. Isso existe especificamente pra impedir que uma
     prompt injection convença o agente a instalar código malicioso durante
     uma conversa. `plugin_manager.py` não é carregado por `tool_loader.py`
     e não aparece na lista de ferramentas do agente.

  2. O manifest fixa um hash SHA-256 do código (`code_sha256`). Se o
     conteúdo na URL mudar depois de publicado — o clássico ataque de
     supply-chain onde o autor troca o arquivo depois que alguém revisou —
     a verificação falha alto e a instalação é abortada.

  3. `stage()` só baixa e verifica o hash — grava em
     `plugins/<nome>.staged.py`, nada executável ainda. `approve()` move
     pra `plugins/<nome>.py` — mas só depois de VOCÊ ter lido o código.
     Mesmo aprovado, só fica invocável se `PLUGINS_ENABLED=True` em
     config.py (desligado por padrão — opt-in explícito).

  4. Quando habilitado, o código do plugin roda DENTRO do sandbox WASM
     (mesma isolação do `run_python`: sem rede, `/workspace` read-only,
     memória e timeout limitados) via `tools.run_python_tool._run_in_wasm`
     — nunca via `import` direto no processo do agente. Um plugin malicioso
     tem o mesmo teto de dano que código Python arbitrário rodando via
     `run_python`, não mais que isso.

Uso (manual, no terminal — nunca chamado pelo agente):

    python plugin_manager.py stage <manifest_url>
    python plugin_manager.py list
    python plugin_manager.py approve <nome>
    python plugin_manager.py run <nome> '{"param": "valor"}'   # só com PLUGINS_ENABLED=True

Formato do manifest (JSON, hospedado pelo autor do plugin):
    {
      "name": "meu_plugin",
      "version": "1.0.0",
      "description": "o que a tool faz",
      "code_url": "https://.../meu_plugin.py",
      "code_sha256": "<hash sha256 do conteudo de code_url>"
    }

O arquivo em code_url precisa definir uma função `run(params: dict) -> str`
— mesma assinatura das tools nativas em tools/*_tool.py.
"""
import hashlib
import json
import logging
import os
import re
import sys

log = logging.getLogger(__name__)

_PROJECT    = os.path.dirname(os.path.abspath(__file__))
PLUGINS_DIR = os.path.join(_PROJECT, "plugins")

REQUIRED_MANIFEST_FIELDS = {"name", "version", "description", "code_url", "code_sha256"}


class PluginError(Exception):
    pass


def _safe_name(name: str) -> str:
    safe = re.sub(r"[^\w\-]", "_", name).strip("_")
    if not safe:
        raise PluginError("nome de plugin inválido")
    return safe


def fetch_manifest(manifest_url: str) -> dict:
    import requests
    r = requests.get(manifest_url, timeout=15)
    r.raise_for_status()
    manifest = r.json()
    missing = REQUIRED_MANIFEST_FIELDS - manifest.keys()
    if missing:
        raise PluginError(f"manifest incompleto — faltando campos: {missing}")
    return manifest


def stage(manifest_url: str) -> str:
    """Baixa o código do plugin, verifica o hash contra o manifest, e salva
    em plugins/<nome>.staged.py. NÃO fica executável — precisa approve()."""
    import requests

    manifest = fetch_manifest(manifest_url)
    name = _safe_name(manifest["name"])

    r = requests.get(manifest["code_url"], timeout=15)
    r.raise_for_status()
    code = r.text

    actual_hash   = hashlib.sha256(code.encode("utf-8")).hexdigest()
    expected_hash = str(manifest["code_sha256"]).lower()
    if actual_hash != expected_hash:
        raise PluginError(
            "HASH NÃO BATE — possível supply-chain attack (o código na URL mudou "
            "desde que o manifest foi publicado, ou o manifest está errado). "
            f"esperado={expected_hash} obtido={actual_hash}. Instalação abortada."
        )

    os.makedirs(PLUGINS_DIR, exist_ok=True)
    staged_path   = os.path.join(PLUGINS_DIR, f"{name}.staged.py")
    manifest_path = os.path.join(PLUGINS_DIR, f"{name}.manifest.json")
    with open(staged_path, "w", encoding="utf-8") as f:
        f.write(code)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    log.info("Plugin '%s' estagiado (hash OK) — revise %s antes de aprovar", name, staged_path)
    return name


def list_staged() -> list[dict]:
    if not os.path.isdir(PLUGINS_DIR):
        return []
    out = []
    for fname in sorted(os.listdir(PLUGINS_DIR)):
        if fname.endswith(".staged.py"):
            out.append({"name": fname[: -len(".staged.py")], "status": "staged"})
        elif fname.endswith(".py"):
            out.append({"name": fname[: -len(".py")], "status": "approved"})
    return out


def approve(name: str):
    """Move plugins/<nome>.staged.py -> plugins/<nome>.py — só depois de
    você ter LIDO o código. Ainda assim só roda se PLUGINS_ENABLED=True."""
    name = _safe_name(name)
    staged_path = os.path.join(PLUGINS_DIR, f"{name}.staged.py")
    active_path = os.path.join(PLUGINS_DIR, f"{name}.py")
    if not os.path.isfile(staged_path):
        raise PluginError(f"'{name}' não está estagiado — rode stage() primeiro")
    os.replace(staged_path, active_path)
    log.info("Plugin '%s' aprovado -> %s", name, active_path)


def run_plugin(name: str, params: dict) -> str:
    """Executa o plugin aprovado DENTRO do sandbox WASM (mesma isolação do
    run_python — sem rede, /workspace read-only, memória/timeout limitados).
    Requer PLUGINS_ENABLED=True em config.py."""
    from config import PLUGINS_ENABLED
    if not PLUGINS_ENABLED:
        raise PluginError("PLUGINS_ENABLED=False em config.py — plugins desligados por padrão")

    name = _safe_name(name)
    active_path = os.path.join(PLUGINS_DIR, f"{name}.py")
    if not os.path.isfile(active_path):
        raise PluginError(f"'{name}' não está aprovado — rode approve() primeiro")

    with open(active_path, encoding="utf-8") as f:
        plugin_code = f.read()

    # Shim: cola o código do plugin com uma chamada a run(params) no final,
    # onde params vem de um repr() de string JSON — seguro contra injeção
    # porque repr() gera um literal Python corretamente escapado, não
    # interpolação direta do texto do usuário no código.
    params_json = json.dumps(params, ensure_ascii=False)
    shim = (
        plugin_code
        + "\n\nimport json as _json\n"
        + f"_result = run(_json.loads({params_json!r}))\n"
        + "print(_result if isinstance(_result, str) else _json.dumps(_result, ensure_ascii=False))\n"
    )

    from tools.run_python_tool import _run_in_wasm, _wasm_available
    if not _wasm_available():
        raise PluginError("sandbox WASM indisponível (rode download_wasm_sandbox.bat) — execução de plugin bloqueada")

    output, exit_code, elapsed = _run_in_wasm(shim)
    if exit_code != 0:
        raise PluginError(f"plugin '{name}' falhou (exit={exit_code}):\n{output}")
    return output


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    try:
        if cmd == "stage" and len(sys.argv) == 3:
            stage(sys.argv[2])
        elif cmd == "list":
            staged = list_staged()
            if not staged:
                print("Nenhum plugin estagiado ou aprovado.")
            for p in staged:
                print(f"  {p['name']} — {p['status']}")
        elif cmd == "approve" and len(sys.argv) == 3:
            approve(sys.argv[2])
        elif cmd == "run" and len(sys.argv) == 4:
            print(run_plugin(sys.argv[2], json.loads(sys.argv[3])))
        else:
            print(__doc__)
            sys.exit(1)
    except PluginError as e:
        print(f"Erro: {e}")
        sys.exit(1)
