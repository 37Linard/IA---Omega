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

  2b. Hash sozinho só prova que "o código bate com o que está escrito no
      manifest" — não prova QUEM escreveu o manifest. Qualquer atacante
      controla os dois lados (manifest + code_url) e o hash sempre vai
      bater com ele mesmo. Por isso o manifest também exige `author_id` +
      `signature` (Ed25519) — a assinatura só verifica contra uma chave
      pública que VOCÊ adicionou manualmente em
      `plugins/trusted_authors.json` (`trust_author()`/`python
      plugin_manager.py trust`), nunca baixada automaticamente. Sem isso
      seria só TOFU (confia na 1ª vez que vê), que não protege nada contra
      o 1º contato malicioso.

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

  5. Desde a v1.6, `stage`/`approve`/`trust_author`/`untrust_author` também
     ficam expostos via API HTTP (`api.py`, rotas `/plugins/...`) — travados
     atrás da mesma senha (`AUTH_PASSWORD`) que protege `/export/data`. Isso
     não reabre o vetor de prompt injection do ponto 1: essas rotas nunca
     foram (e continuam não sendo) carregadas por `tool_loader.py`, o agente
     não tem — e nunca teve — como chamá-las. O que muda é só "alcançável
     também por quem tem a senha remota", não "alcançável pelo agente".

Uso (manual, no terminal — nunca chamado pelo agente):

    python plugin_manager.py stage <manifest_url>
    python plugin_manager.py list
    python plugin_manager.py approve <nome>
    python plugin_manager.py run <nome> '{"param": "valor"}'   # só com PLUGINS_ENABLED=True

    # Do lado do AUTOR do plugin (gera chave, assina o manifest):
    python plugin_manager.py keygen
    python plugin_manager.py sign <name> <version> <code_sha256> <chave_privada_hex>

    # Do lado do OPERADOR (você — decide em quem confiar):
    python plugin_manager.py trust <author_id> <chave_publica_hex>
    python plugin_manager.py untrust <author_id>
    python plugin_manager.py trusted

Descoberta (marketplace) — NÃO existe um registry central "oficial" desse
projeto (é pessoal/local). PLUGIN_REGISTRY_URLS em config.py é uma lista
vazia por padrão — você adiciona URL(s) http(s) ou caminho(s) de arquivo
local que confia (o formato de cada registry está em
plugins_registry.example.json). "search"/"registry-list" só LISTAM, nunca
instalam nada sozinhos — o modelo de segurança acima (hash + assinatura +
aprovação manual) continua idêntico depois de achar um manifest_url:

    python plugin_manager.py search <termo>
    python plugin_manager.py registry-list [url_ou_caminho]   # todos configurados se omitido

Formato do manifest (JSON, hospedado pelo autor do plugin):
    {
      "name": "meu_plugin",
      "version": "1.0.0",
      "description": "o que a tool faz",
      "code_url": "https://.../meu_plugin.py",
      "code_sha256": "<hash sha256 do conteudo de code_url>",
      "author_id": "<identificador do autor, escolhido por ele>",
      "signature": "<assinatura Ed25519 hex — ver 'python plugin_manager.py sign'>"
    }

O autor assina com `python plugin_manager.py keygen` (gera par de chaves,
guarda a privada em segredo) e `python plugin_manager.py sign <name>
<version> <code_sha256> <chave_privada_hex>`. Você (operador) recebe a
chave PÚBLICA do autor por um canal que confia (não pelo próprio manifest —
isso seria confiar no atacante pra dizer se ele é confiável) e roda
`python plugin_manager.py trust <author_id> <chave_publica_hex>` antes de
instalar qualquer plugin desse autor.

O arquivo em code_url precisa definir uma função `run(params: dict) -> str`
— mesma assinatura das tools nativas em tools/*_tool.py.
"""
import hashlib
import json
import logging
import os
import re
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

log = logging.getLogger(__name__)

_PROJECT             = os.path.dirname(os.path.abspath(__file__))
PLUGINS_DIR          = os.path.join(_PROJECT, "plugins")
TRUSTED_AUTHORS_FILE = os.path.join(PLUGINS_DIR, "trusted_authors.json")

REQUIRED_MANIFEST_FIELDS = {"name", "version", "description", "code_url", "code_sha256", "author_id", "signature"}


class PluginError(Exception):
    pass


# ---------------------------------------------------------------------------
# Confiança de autor — chaves públicas Ed25519 adicionadas manualmente pelo
# operador (nunca baixadas automaticamente de lugar nenhum)
# ---------------------------------------------------------------------------
def _load_trusted_authors() -> dict[str, str]:
    if not os.path.isfile(TRUSTED_AUTHORS_FILE):
        return {}
    try:
        with open(TRUSTED_AUTHORS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_trusted_authors(authors: dict[str, str]):
    os.makedirs(PLUGINS_DIR, exist_ok=True)
    with open(TRUSTED_AUTHORS_FILE, "w", encoding="utf-8") as f:
        json.dump(authors, f, indent=2, ensure_ascii=False)


def trust_author(author_id: str, pubkey_hex: str):
    """Adiciona/atualiza a chave pública de um autor confiado. Valida que a
    chave é uma Ed25519 pública de verdade antes de gravar — erro de digitação
    na hex vira `PluginError` na hora, não um "confiado" quebrado em silêncio."""
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pubkey_hex))
    except Exception as e:
        raise PluginError(f"chave pública inválida pra '{author_id}': {e}")
    authors = _load_trusted_authors()
    authors[author_id] = pubkey_hex.lower()
    _save_trusted_authors(authors)
    log.info("Autor '%s' confiado (pubkey %s...)", author_id, pubkey_hex[:12])


def untrust_author(author_id: str):
    authors = _load_trusted_authors()
    if authors.pop(author_id, None) is not None:
        _save_trusted_authors(authors)
        log.info("Autor '%s' removido da lista de confiança", author_id)


def list_trusted_authors() -> list[dict]:
    return [{"author_id": a, "pubkey": k} for a, k in sorted(_load_trusted_authors().items())]


def _signing_payload(name: str, version: str, code_sha256: str) -> bytes:
    """Payload canônico assinado/verificado — inclui name+version além do
    hash pra uma assinatura válida de UM plugin não poder ser reaproveitada
    (replay) pra fazer outro plugin (ou outra versão) parecer assinado."""
    return f"{name}|{version}|{code_sha256.lower()}".encode("utf-8")


def generate_keypair() -> tuple[str, str]:
    """Utilitário pro AUTOR do plugin gerar seu par de chaves. Retorna
    (chave_privada_hex, chave_publica_hex) — a privada nunca sai da máquina
    do autor, só a pública vai pro operador confiar."""
    priv = Ed25519PrivateKey.generate()
    return priv.private_bytes_raw().hex(), priv.public_key().public_bytes_raw().hex()


def sign_payload(name: str, version: str, code_sha256: str, private_key_hex: str) -> str:
    """Utilitário pro AUTOR assinar o manifest antes de publicar."""
    try:
        priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(private_key_hex))
    except Exception as e:
        raise PluginError(f"chave privada inválida: {e}")
    return priv.sign(_signing_payload(name, version, code_sha256)).hex()


def _verify_signature(manifest: dict, code_sha256: str):
    """Verifica manifest['signature'] contra a chave pública confiada de
    manifest['author_id']. Autor não-confiado ou assinatura inválida ->
    PluginError, mesma severidade do hash não bater."""
    author_id = str(manifest["author_id"])
    authors = _load_trusted_authors()
    pubkey_hex = authors.get(author_id)
    if not pubkey_hex:
        raise PluginError(
            f"AUTOR NÃO CONFIADO: '{author_id}'. Adicione a chave pública dele com "
            f"'python plugin_manager.py trust {author_id} <chave_publica_hex>' "
            "(recebida por um canal que você confia) antes de instalar. Instalação abortada."
        )
    try:
        pubkey = Ed25519PublicKey.from_public_bytes(bytes.fromhex(pubkey_hex))
        signature = bytes.fromhex(str(manifest["signature"]))
        pubkey.verify(signature, _signing_payload(manifest["name"], manifest["version"], code_sha256))
    except Exception as e:
        raise PluginError(
            f"ASSINATURA INVÁLIDA pra '{manifest['name']}' do autor '{author_id}' — "
            f"o manifest pode ter sido adulterado ou forjado. Instalação abortada. ({e})"
        )


def _safe_name(name: str) -> str:
    safe = re.sub(r"[^\w\-]", "_", name).strip("_")
    if not safe:
        raise PluginError("nome de plugin inválido")
    return safe


# ---------------------------------------------------------------------------
# Descoberta (marketplace) — registry é só um índice JSON (nome/descrição/
# manifest_url/tags), listado ou pesquisado. NUNCA instala nada sozinho —
# achar um manifest_url aqui não pula hash nem assinatura, só poupa o
# operador de já saber a URL do manifest de cor.
# ---------------------------------------------------------------------------
REQUIRED_REGISTRY_ENTRY_FIELDS = {"name", "description", "manifest_url"}


def fetch_registry(registry_url: str) -> list[dict]:
    """Busca um índice de plugins de uma URL http(s) ou caminho de arquivo
    local. Entrada inválida/incompleta é pulada com aviso (não derruba o
    registry inteiro por causa de UM item malformado)."""
    if registry_url.startswith("http://") or registry_url.startswith("https://"):
        import requests
        r = requests.get(registry_url, timeout=15)
        r.raise_for_status()
        data = r.json()
    else:
        with open(registry_url, encoding="utf-8") as f:
            data = json.load(f)

    if not isinstance(data, list):
        raise PluginError(f"registry '{registry_url}' mal formado — esperava uma lista de plugins")

    valid = []
    for entry in data:
        if not isinstance(entry, dict) or REQUIRED_REGISTRY_ENTRY_FIELDS - entry.keys():
            log.warning("fetch_registry: entrada inválida em '%s', pulando: %r", registry_url, entry)
            continue
        valid.append(entry)
    return valid


def search_registries(query: str, registry_urls: list[str] | None = None) -> list[dict]:
    """Pesquisa por nome/descrição/tags em todos os registries configurados
    (config.PLUGIN_REGISTRY_URLS, ou os passados explicitamente). Registry
    fora do ar ou malformado é pulado com aviso, não derruba a busca inteira
    nos outros registries configurados."""
    if registry_urls is None:
        registry_urls = list_registry_urls()

    query_l = query.lower().strip()
    results = []
    for url in registry_urls:
        try:
            entries = fetch_registry(url)
        except Exception as e:
            log.warning("search_registries: registry '%s' indisponível (%s), pulando", url, e)
            continue
        for entry in entries:
            haystack = " ".join([
                str(entry.get("name", "")),
                str(entry.get("description", "")),
                " ".join(str(t) for t in entry.get("tags", [])),
            ]).lower()
            if not query_l or query_l in haystack:
                results.append({**entry, "_registry": url})
    return results


# ---------------------------------------------------------------------------
# Registries em runtime — adicionadas via API/UI, sobrepõem config.py sem
# reiniciar (mesmo padrão de orchestrator._runtime_models). Não persistem em
# disco de propósito: virar permanente é decisão de editar config.py, igual
# já documentado no topo deste arquivo.
# ---------------------------------------------------------------------------
_runtime_registry_urls: list[str] = []


def list_registry_urls() -> list[str]:
    from config import PLUGIN_REGISTRY_URLS
    merged = list(PLUGIN_REGISTRY_URLS)
    for url in _runtime_registry_urls:
        if url not in merged:
            merged.append(url)
    return merged


def add_registry_url(url: str) -> None:
    if url not in list_registry_urls():
        _runtime_registry_urls.append(url)
        log.info("Registry adicionada em runtime: %s", url)


def remove_registry_url(url: str) -> None:
    if url in _runtime_registry_urls:
        _runtime_registry_urls.remove(url)
        log.info("Registry removida (runtime): %s", url)


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

    # Hash só prova "código bate com o manifest" — não prova quem escreveu o
    # manifest. Assinatura verifica contra uma chave que O OPERADOR escolheu
    # confiar antes, não algo que o próprio manifest pode alegar sozinho.
    _verify_signature(manifest, actual_hash)

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
        elif cmd == "keygen":
            priv_hex, pub_hex = generate_keypair()
            print(f"chave privada (GUARDE EM SEGREDO): {priv_hex}")
            print(f"chave pública (envie pro operador confiar):  {pub_hex}")
        elif cmd == "sign" and len(sys.argv) == 6:
            print(sign_payload(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]))
        elif cmd == "trust" and len(sys.argv) == 4:
            trust_author(sys.argv[2], sys.argv[3])
        elif cmd == "untrust" and len(sys.argv) == 3:
            untrust_author(sys.argv[2])
        elif cmd == "trusted":
            trusted = list_trusted_authors()
            if not trusted:
                print("Nenhum autor confiado.")
            for t in trusted:
                print(f"  {t['author_id']} — {t['pubkey'][:16]}...")
        elif cmd == "search" and len(sys.argv) == 3:
            hits = search_registries(sys.argv[2])
            if not hits:
                print("Nada encontrado (ou nenhum registry em PLUGIN_REGISTRY_URLS ainda).")
            for h in hits:
                print(f"  {h['name']} — {h['description']}  [{h['manifest_url']}]")
        elif cmd == "registry-list":
            urls = [sys.argv[2]] if len(sys.argv) == 3 else None
            hits = search_registries("", registry_urls=urls)
            if not hits:
                print("Nenhum plugin listado (ou nenhum registry configurado).")
            for h in hits:
                print(f"  {h['name']} — {h['description']}  [{h['manifest_url']}]")
        else:
            print(__doc__)
            sys.exit(1)
    except PluginError as e:
        print(f"Erro: {e}")
        sys.exit(1)
