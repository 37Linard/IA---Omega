# Plugin Marketplace UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the existing `plugin_manager.py` marketplace flow (search registries → stage → review code → approve, plus trusted-author management) through `api.py` REST endpoints and a new modal in `frontend/components/Header.tsx`, so the operator can do the whole flow from the browser instead of a Python REPL/CLI.

**Architecture:** Thin REST wrappers in `api.py` around the pure functions already in `plugin_manager.py` (no new business logic in the API layer — mirrors how `/specialist-models` wraps `orchestrator.py`). One new runtime-override concept added to `plugin_manager.py` (`_runtime_registry_urls`, same pattern as `orchestrator._runtime_models`) so registries can be added from the UI without editing `config.py`. Frontend follows the existing "modal function inside `Header.tsx`" convention (see `AuditLogModal`, `SpecialistModelsModal`) — no new component file, since every other modal in this codebase lives there too.

**Tech Stack:** FastAPI (`api.py`), Python stdlib + `requests` (`plugin_manager.py`), Next.js/React/TypeScript (`frontend/`), `pytest` + `monkeypatch` (backend tests, no `TestClient` — see Global Constraints).

## Global Constraints

- **`stage`/`approve`/`trust_author`/`untrust_author` API endpoints require `Depends(check_auth)`** (same Basic Auth password as `/export/data`), per the security decision in the spec — this was a deliberate CLI-only design in `plugin_manager.py`, being relaxed to "CLI or authenticated HTTP", not to "anyone on the network."
- **`api.py` has zero existing tests and is never imported by any test file** — importing it starts real scheduler/watcher threads (`_scheduler.start(...)`, `_watcher.start()` at module scope). Do not add a `TestClient(app)` test as part of this plan; new logic goes in `plugin_manager.py` (testable in isolation, matching `tests/test_plugin_registry_discovery.py`) and the new endpoints are validated live by the user, matching every other endpoint in this file.
- **No new file for the modal.** `Header.tsx` already holds `Modal`, `ProfileModal`, `HealthModal`, `RagModal`, `AuditLogModal`, `SpecialistModelsModal` — follow that convention, don't split it out unilaterally.
- **Follow `frontend/AGENTS.md`**: this Next.js version has breaking changes vs. training data — check `node_modules/next/dist/docs/` before using any Next.js API you're not 100% sure of. (Not expected to be needed here — no new routes/pages, just a component inside the existing client tree — but the file exists, so note it.)
- **`PluginError` messages are already human-readable** — endpoints re-raise them as `HTTPException(status_code=400, detail=str(e))` verbatim, no rewording.

---

### Task 1: Runtime registry overrides in `plugin_manager.py`

**Files:**
- Modify: `plugin_manager.py:250-275` (existing `search_registries`, need it to default to the merged list instead of only `config.PLUGIN_REGISTRY_URLS`)
- Modify: `plugin_manager.py` — insert new functions right after `search_registries` (currently ends line 275), before `fetch_manifest` (currently line 278)
- Test: `tests/test_plugin_registry_runtime.py` (new)

**Interfaces:**
- Produces: `add_registry_url(url: str) -> None`, `remove_registry_url(url: str) -> None`, `list_registry_urls() -> list[str]` — all in `plugin_manager.py`, importable as `pm.add_registry_url` etc. `list_registry_urls()` returns `config.PLUGIN_REGISTRY_URLS` (in order) followed by any runtime-added URLs not already in that list (no duplicates).
- Consumes: nothing new — `config.PLUGIN_REGISTRY_URLS` (already exists).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_plugin_registry_runtime.py
"""Registries adicionadas via API/UI ficam só em memória (mesmo padrão do
_runtime_models em orchestrator.py) -- não sobrevivem a restart, não tocam
config.py. list_registry_urls() funde config + runtime sem duplicar."""
import plugin_manager as pm


def test_list_registry_urls_starts_with_config_only(monkeypatch):
    monkeypatch.setattr(pm, "_runtime_registry_urls", [])
    monkeypatch.setattr("config.PLUGIN_REGISTRY_URLS", ["https://a.example/reg.json"])

    assert pm.list_registry_urls() == ["https://a.example/reg.json"]


def test_add_registry_url_appends_to_runtime_list(monkeypatch):
    monkeypatch.setattr(pm, "_runtime_registry_urls", [])
    monkeypatch.setattr("config.PLUGIN_REGISTRY_URLS", [])

    pm.add_registry_url("https://b.example/reg.json")

    assert pm.list_registry_urls() == ["https://b.example/reg.json"]


def test_add_registry_url_does_not_duplicate_config_entry(monkeypatch):
    monkeypatch.setattr(pm, "_runtime_registry_urls", [])
    monkeypatch.setattr("config.PLUGIN_REGISTRY_URLS", ["https://a.example/reg.json"])

    pm.add_registry_url("https://a.example/reg.json")

    assert pm.list_registry_urls() == ["https://a.example/reg.json"]


def test_remove_registry_url_only_removes_runtime_entry(monkeypatch):
    monkeypatch.setattr(pm, "_runtime_registry_urls", ["https://b.example/reg.json"])
    monkeypatch.setattr("config.PLUGIN_REGISTRY_URLS", ["https://a.example/reg.json"])

    pm.remove_registry_url("https://a.example/reg.json")  # veio do config, ignora
    pm.remove_registry_url("https://b.example/reg.json")  # veio do runtime, remove

    assert pm.list_registry_urls() == ["https://a.example/reg.json"]


def test_search_registries_uses_merged_list_by_default(monkeypatch):
    calls = []

    def fake_fetch_registry(url):
        calls.append(url)
        return []

    monkeypatch.setattr(pm, "fetch_registry", fake_fetch_registry)
    monkeypatch.setattr(pm, "_runtime_registry_urls", ["https://runtime.example/reg.json"])
    monkeypatch.setattr("config.PLUGIN_REGISTRY_URLS", ["https://config.example/reg.json"])

    pm.search_registries("qualquer")

    assert calls == ["https://config.example/reg.json", "https://runtime.example/reg.json"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_plugin_registry_runtime.py -v`
Expected: FAIL — `AttributeError: module 'plugin_manager' has no attribute '_runtime_registry_urls'` (and similar for the other new names).

- [ ] **Step 3: Implement in `plugin_manager.py`**

Insert after the existing `search_registries` function (right before `def fetch_manifest`):

```python
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
```

Then change `search_registries`'s default from reading `config.PLUGIN_REGISTRY_URLS` directly to calling `list_registry_urls()`:

```python
def search_registries(query: str, registry_urls: list[str] | None = None) -> list[dict]:
    """..."""  # docstring unchanged
    if registry_urls is None:
        registry_urls = list_registry_urls()
    ...  # resto da função sem mudança
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_plugin_registry_runtime.py -v`
Expected: PASS (5 passed)

- [ ] **Step 5: Run full suite to check for regressions**

Run: `pytest -q`
Expected: all green, no new failures (existing `test_plugin_registry_discovery.py` still passes — it calls `search_registries(query, registry_urls=[...])` explicitly in every test, so the new default doesn't affect it).

- [ ] **Step 6: Commit**

```bash
git add plugin_manager.py tests/test_plugin_registry_runtime.py
git commit -m "feat: registries de plugin em runtime (add/remove sem restart)"
```

---

### Task 2: Read-only plugin endpoints in `api.py`

**Files:**
- Modify: `api.py` — add new endpoints after the `/specialist-models` block (currently ends line 576, right before `@app.get("/kg/stats")` at line 579)

**Interfaces:**
- Consumes: `pm.list_registry_urls()`, `pm.search_registries(query)`, `pm.list_staged()`, `pm.list_trusted_authors()`, `pm._safe_name(name)`, `pm.PLUGINS_DIR`, `pm.PluginError` (Task 1 + existing `plugin_manager.py`).
- Produces: `GET /plugins/registries`, `GET /plugins/search`, `GET /plugins/staged`, `GET /plugins/staged/{name}/code`, `GET /plugins/trusted-authors` — consumed by Task 4 (`frontend/lib/api.ts`).

No test step for this task — see Global Constraints (`api.py` has no test harness; these are thin wrappers with no branching logic beyond what Task 1 already tests). Validated live in Task 7.

- [ ] **Step 1: Implement the endpoints**

Insert after line 576 (`return {"specialist": specialist, "model": model}`, end of `post_specialist_model`), before `@app.get("/kg/stats")`:

```python
@app.get("/plugins/registries")
async def list_plugin_registries():
    import plugin_manager as pm
    return {"registries": pm.list_registry_urls()}


@app.get("/plugins/search")
async def search_plugins(q: str = ""):
    import plugin_manager as pm
    try:
        results = await asyncio.get_running_loop().run_in_executor(
            executor, pm.search_registries, q
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"results": results}


@app.get("/plugins/staged")
async def list_staged_plugins():
    import plugin_manager as pm
    return {"plugins": pm.list_staged()}


@app.get("/plugins/staged/{name}/code")
async def get_staged_plugin_code(name: str):
    import plugin_manager as pm
    try:
        safe_name = pm._safe_name(name)
    except pm.PluginError as e:
        raise HTTPException(status_code=400, detail=str(e))
    staged_path = os.path.join(pm.PLUGINS_DIR, f"{safe_name}.staged.py")
    if not os.path.isfile(staged_path):
        raise HTTPException(status_code=404, detail=f"'{name}' não está estagiado")
    with open(staged_path, encoding="utf-8") as f:
        return {"name": safe_name, "code": f.read()}


@app.get("/plugins/trusted-authors")
async def list_trusted_plugin_authors():
    import plugin_manager as pm
    return {"authors": pm.list_trusted_authors()}
```

`os` is already imported at module scope via `import os` — check line ~1-20; if it's not there yet, add `import os` to the top-level import block (used elsewhere in the file already for path joins, e.g. `os.path` appears in the workspace image endpoint around line 317 — reuse, don't re-import locally).

- [ ] **Step 2: Manual smoke check**

Run: `python -c "import api"` — must not raise (catches typos/syntax errors without starting uvicorn). This is the same style of check already used informally in this codebase before live-testing new endpoints.

- [ ] **Step 3: Commit**

```bash
git add api.py
git commit -m "feat: endpoints de leitura do plugin marketplace (registries/search/staged/autores)"
```

---

### Task 3: Write plugin endpoints in `api.py` (auth-gated)

**Files:**
- Modify: `api.py` — add endpoints right after the ones from Task 2

**Interfaces:**
- Consumes: `pm.add_registry_url`, `pm.remove_registry_url` (Task 1), `pm.stage`, `pm.approve`, `pm.trust_author`, `pm.untrust_author`, `pm.PluginError` (existing).
- Produces: `POST /plugins/registries`, `DELETE /plugins/registries`, `POST /plugins/stage`, `POST /plugins/approve`, `POST /plugins/trust`, `DELETE /plugins/trust/{author_id}` — consumed by Task 4.

- [ ] **Step 1: Implement the endpoints**

```python
@app.post("/plugins/registries")
async def add_plugin_registry(body: dict, _rl=Depends(_check_rate_limit)):
    import plugin_manager as pm
    url = body.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url obrigatório")
    pm.add_registry_url(url)
    return {"registries": pm.list_registry_urls()}


@app.delete("/plugins/registries")
async def remove_plugin_registry(url: str, _rl=Depends(_check_rate_limit)):
    import plugin_manager as pm
    pm.remove_registry_url(url.strip())
    return {"registries": pm.list_registry_urls()}


@app.post("/plugins/stage")
async def stage_plugin(
    body: dict,
    _rl=Depends(_check_rate_limit),
    credentials: HTTPBasicCredentials = Depends(check_auth),
):
    import plugin_manager as pm
    manifest_url = body.get("manifest_url", "").strip()
    if not manifest_url:
        raise HTTPException(status_code=400, detail="manifest_url obrigatório")
    try:
        name = await asyncio.get_running_loop().run_in_executor(
            executor, pm.stage, manifest_url
        )
    except pm.PluginError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"name": name, "status": "staged"}


@app.post("/plugins/approve")
async def approve_plugin(
    body: dict,
    _rl=Depends(_check_rate_limit),
    credentials: HTTPBasicCredentials = Depends(check_auth),
):
    import plugin_manager as pm
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name obrigatório")
    try:
        pm.approve(name)
    except pm.PluginError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"name": name, "status": "approved"}


@app.post("/plugins/trust")
async def trust_plugin_author(
    body: dict,
    _rl=Depends(_check_rate_limit),
    credentials: HTTPBasicCredentials = Depends(check_auth),
):
    import plugin_manager as pm
    author_id  = body.get("author_id", "").strip()
    pubkey_hex = body.get("pubkey", "").strip()
    if not author_id or not pubkey_hex:
        raise HTTPException(status_code=400, detail="author_id e pubkey obrigatórios")
    try:
        pm.trust_author(author_id, pubkey_hex)
    except pm.PluginError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"authors": pm.list_trusted_authors()}


@app.delete("/plugins/trust/{author_id}")
async def untrust_plugin_author(
    author_id: str,
    _rl=Depends(_check_rate_limit),
    credentials: HTTPBasicCredentials = Depends(check_auth),
):
    import plugin_manager as pm
    pm.untrust_author(author_id)
    return {"authors": pm.list_trusted_authors()}
```

- [ ] **Step 2: Manual smoke check**

Run: `python -c "import api"` — must not raise.

- [ ] **Step 3: Update `plugin_manager.py` docstring**

The module docstring (top of file, lines 1-93) currently says installation is "SEMPRE uma ação manual do operador... rodando este script na linha de comando" and lists only CLI usage. Add a short paragraph after the numbered security model (after point 4, before "Uso (manual, no terminal...)"):

```python
  5. Desde a v1.6, `stage`/`approve`/`trust_author`/`untrust_author` também
     ficam expostos via API HTTP (`api.py`, rotas `/plugins/...`) — travados
     atrás da mesma senha (`AUTH_PASSWORD`) que protege `/export/data`. Isso
     não reabre o vetor de prompt injection do ponto 1: essas rotas nunca
     foram (e continuam não sendo) carregadas por `tool_loader.py`, o agente
     não tem — e nunca teve — como chamá-las. O que muda é só "alcançável
     também por quem tem a senha remota", não "alcançável pelo agente".
```

- [ ] **Step 4: Commit**

```bash
git add api.py plugin_manager.py
git commit -m "feat: endpoints de escrita do plugin marketplace (stage/approve/trust, atras de auth)"
```

---

### Task 4: Frontend API client (`frontend/lib/api.ts`)

**Files:**
- Modify: `frontend/lib/api.ts` — add after `setSpecialistModel` (currently ends line 136), before `fetchTemplates`

**Interfaces:**
- Consumes: the `req<T>()` helper already at the top of the file, `API_BASE` from `./utils`.
- Produces: `PluginRegistryEntry`, `PluginSearchResult`, `StagedPlugin`, `TrustedAuthor` types + `fetchPluginRegistries`, `addPluginRegistry`, `removePluginRegistry`, `searchPlugins`, `stagePlugin`, `fetchStagedPlugins`, `fetchStagedPluginCode`, `approvePlugin`, `fetchTrustedAuthors`, `trustPluginAuthor`, `untrustPluginAuthor` — consumed by Task 5/6 (`Header.tsx`).

- [ ] **Step 1: Add types + functions**

```typescript
export interface PluginSearchResult {
  name: string
  description: string
  manifest_url: string
  author_id?: string
  tags?: string[]
  _registry: string
}

export interface StagedPlugin {
  name: string
  status: 'staged' | 'approved'
}

export interface TrustedAuthor {
  author_id: string
  pubkey: string
}

export async function fetchPluginRegistries(): Promise<{ registries: string[] }> {
  return req('/plugins/registries')
}

export async function addPluginRegistry(url: string): Promise<{ registries: string[] }> {
  return req('/plugins/registries', { method: 'POST', body: JSON.stringify({ url }) })
}

export async function removePluginRegistry(url: string): Promise<{ registries: string[] }> {
  return req(`/plugins/registries?url=${encodeURIComponent(url)}`, { method: 'DELETE' })
}

export async function searchPlugins(q: string): Promise<{ results: PluginSearchResult[] }> {
  return req(`/plugins/search?q=${encodeURIComponent(q)}`)
}

export async function stagePlugin(manifestUrl: string): Promise<{ name: string; status: string }> {
  return req('/plugins/stage', { method: 'POST', body: JSON.stringify({ manifest_url: manifestUrl }) })
}

export async function fetchStagedPlugins(): Promise<{ plugins: StagedPlugin[] }> {
  return req('/plugins/staged')
}

export async function fetchStagedPluginCode(name: string): Promise<{ name: string; code: string }> {
  return req(`/plugins/staged/${encodeURIComponent(name)}/code`)
}

export async function approvePlugin(name: string): Promise<{ name: string; status: string }> {
  return req('/plugins/approve', { method: 'POST', body: JSON.stringify({ name }) })
}

export async function fetchTrustedAuthors(): Promise<{ authors: TrustedAuthor[] }> {
  return req('/plugins/trusted-authors')
}

export async function trustPluginAuthor(authorId: string, pubkey: string): Promise<{ authors: TrustedAuthor[] }> {
  return req('/plugins/trust', { method: 'POST', body: JSON.stringify({ author_id: authorId, pubkey }) })
}

export async function untrustPluginAuthor(authorId: string): Promise<{ authors: TrustedAuthor[] }> {
  return req(`/plugins/trust/${encodeURIComponent(authorId)}`, { method: 'DELETE' })
}
```

Note: `req<T>()` throws a plain `Error(`HTTP ${res.status}`)` on non-2xx, losing the `PluginError` detail message from the JSON body. Check how `AuditLogModal`/`SpecialistModelsModal` currently surface backend error text — if they also just show a generic "erro" banner (grep `catch` blocks around `setError(true)` in `Header.tsx`), match that (generic banner is fine, consistent with the rest of the file). Do not add per-endpoint error-parsing logic that the rest of the file doesn't have — that would be inconsistent, not better.

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no new errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/api.ts
git commit -m "feat: cliente frontend pros endpoints do plugin marketplace"
```

---

### Task 5: `PluginMarketplaceModal` — Buscar + Estagiados tabs

**Files:**
- Modify: `frontend/components/Header.tsx` — add imports, state, button, and the new modal function

**Interfaces:**
- Consumes: `CodeBlock` from `./CodeBlock` (existing, `<CodeBlock language="python">{code}</CodeBlock>`), the API functions from Task 4, `AuditLogModal`'s custom wide-overlay markup as the layout template (read `Header.tsx:1008-1150` region for the exact skeleton before writing this).
- Produces: `PluginMarketplaceModal` component, rendered conditionally in the same place as `{auditOpen && <AuditLogModal .../>}` (around line 232).

- [ ] **Step 1: Add the icon import and state**

In the `lucide-react` import (line 4), add `Puzzle`:

```typescript
import { Menu, Sun, Moon, User, Heart, Cpu, Database, Trash2, FolderOpen, RefreshCw, CheckCircle, XCircle, Loader2, Layers, GitGraph, LayoutGrid, Workflow, Download, ScrollText, MoreHorizontal, Puzzle } from 'lucide-react'
```

Also import the new API functions and types at the top of `Header.tsx` (wherever the existing `fetchSpecialistModels`/`setSpecialistModel` imports live — grep `from '../lib/api'` in the file and add to that same import statement):

```typescript
import {
  // ...existing imports...
  fetchPluginRegistries, searchPlugins, stagePlugin, fetchStagedPlugins,
  fetchStagedPluginCode, approvePlugin,
  type PluginSearchResult, type StagedPlugin,
} from '../lib/api'
import { CodeBlock } from './CodeBlock'
```

Add state near the other `*Open` flags (line ~26, after `nocOpen`/`workflowOpen`):

```typescript
const [pluginsOpen, setPluginsOpen] = useState(false)
```

- [ ] **Step 2: Add the header button and more-menu entry**

After the `AuditLogModal` button block (`<HeaderBtn onClick={() => setAuditOpen(true)} ...>`, ends line 184), add:

```tsx
<HeaderBtn onClick={() => setPluginsOpen(true)} title="Plugin Marketplace">
  <Puzzle size={15} />
</HeaderBtn>
```

In the `MoreMenu` `items` array (line 195-204), add one more entry, matching the existing style:

```tsx
{ icon: <Puzzle size={15} />, label: 'Plugin Marketplace', onClick: () => setPluginsOpen(true) },
```

Render the modal next to the other conditional renders (after `{auditOpen && <AuditLogModal onClose={() => setAuditOpen(false)} />}`, line 232):

```tsx
{pluginsOpen && <PluginMarketplaceModal onClose={() => setPluginsOpen(false)} />}
```

- [ ] **Step 3: Write the modal — state, data loading, Buscar + Estagiados tabs**

Add this function anywhere in the "modal functions" region of the file (e.g. right after `AuditLogModal`'s closing brace, before `SpecialistModelsModal`). Use `AuditLogModal`'s wide custom overlay (the `<div style={{ position: 'fixed', inset: 0, ... }}>` / inner panel with `maxWidth` wider than the 380px `Modal` base) as the layout skeleton instead of the narrow `Modal` component — copy its overlay/panel/header `style` objects verbatim so visual style stays consistent, only the body content differs.

```tsx
function PluginMarketplaceModal({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<'buscar' | 'estagiados' | 'registries' | 'autores'>('buscar')

  // -- Buscar --
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<PluginSearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState('')

  // -- Estagiados --
  const [staged, setStaged] = useState<StagedPlugin[]>([])
  const [expanded, setExpanded] = useState<string | null>(null)
  const [code, setCode] = useState<Record<string, string>>({})
  const [viewed, setViewed] = useState<Record<string, boolean>>({})
  const [busy, setBusy] = useState<string | null>(null)
  const [stagedError, setStagedError] = useState('')

  const loadStaged = useCallback(async () => {
    try {
      const d = await fetchStagedPlugins()
      setStaged(d.plugins)
      setStagedError('')
    } catch {
      setStagedError('Erro ao carregar plugins estagiados — backend disponível?')
    }
  }, [])

  useEffect(() => { loadStaged() }, [loadStaged])

  const doSearch = async () => {
    setSearching(true)
    setSearchError('')
    try {
      const d = await searchPlugins(query)
      setResults(d.results)
    } catch {
      setSearchError('Erro na busca — cheque se há registries configuradas na aba Registries.')
    } finally {
      setSearching(false)
    }
  }

  const doStage = async (manifestUrl: string) => {
    setBusy(manifestUrl)
    try {
      await stagePlugin(manifestUrl)
      await loadStaged()
      setTab('estagiados')
    } catch (e) {
      setSearchError(e instanceof Error ? e.message : 'Erro ao estagiar plugin')
    } finally {
      setBusy(null)
    }
  }

  const toggleExpand = async (name: string) => {
    if (expanded === name) {
      setExpanded(null)
      return
    }
    setExpanded(name)
    setViewed(v => ({ ...v, [name]: true }))
    if (!code[name]) {
      try {
        const d = await fetchStagedPluginCode(name)
        setCode(c => ({ ...c, [name]: d.code }))
      } catch {
        setCode(c => ({ ...c, [name]: '# erro ao carregar código' }))
      }
    }
  }

  const doApprove = async (name: string) => {
    setBusy(name)
    try {
      await approvePlugin(name)
      await loadStaged()
    } catch (e) {
      setStagedError(e instanceof Error ? e.message : 'Erro ao aprovar plugin')
    } finally {
      setBusy(null)
    }
  }

  const tabBtnStyle = (active: boolean): React.CSSProperties => ({
    padding: '6px 12px',
    fontSize: '12.5px',
    fontWeight: 600,
    color: active ? 'var(--text-primary)' : 'var(--text-muted)',
    borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
    background: 'none',
    cursor: 'pointer',
  })

  return (
    <div
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px' }}
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        style={{
          background: 'var(--surface)',
          border: '1px solid var(--border-strong)',
          borderRadius: 'var(--radius-lg)',
          width: '100%',
          maxWidth: '760px',
          maxHeight: '80vh',
          overflow: 'hidden',
          boxShadow: '0 24px 64px rgba(0,0,0,0.5)',
          display: 'flex',
          flexDirection: 'column',
        }}
        className="anim-fade-up"
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
          <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>Plugin Marketplace</span>
          <button onClick={onClose} style={{ color: 'var(--text-muted)', background: 'none', fontSize: '18px', lineHeight: 1, cursor: 'pointer' }}>×</button>
        </div>

        <div style={{ display: 'flex', gap: '4px', padding: '8px 20px 0', borderBottom: '1px solid var(--border)' }}>
          <button style={tabBtnStyle(tab === 'buscar')} onClick={() => setTab('buscar')}>Buscar</button>
          <button style={tabBtnStyle(tab === 'estagiados')} onClick={() => setTab('estagiados')}>Estagiados</button>
          <button style={tabBtnStyle(tab === 'registries')} onClick={() => setTab('registries')}>Registries</button>
          <button style={tabBtnStyle(tab === 'autores')} onClick={() => setTab('autores')}>Autores confiáveis</button>
        </div>

        <div style={{ padding: '16px 20px', overflowY: 'auto', flex: 1 }}>
          {tab === 'buscar' && (
            <div>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                <input
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') doSearch() }}
                  placeholder="Buscar plugin por nome/descrição/tag..."
                  style={{ flex: 1, padding: '8px 10px', fontSize: '13px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)' }}
                />
                <button onClick={doSearch} disabled={searching} style={{ padding: '8px 14px', fontSize: '12.5px', fontWeight: 600, borderRadius: '8px', background: 'var(--accent)', color: '#fff', cursor: 'pointer' }}>
                  {searching ? 'Buscando...' : 'Buscar'}
                </button>
              </div>
              {searchError && <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '10px' }}>{searchError}</div>}
              {results.map(r => (
                <div key={r.manifest_url} style={{ padding: '10px 12px', border: '1px solid var(--border)', borderRadius: '8px', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>{r.name}</span>
                    <button
                      onClick={() => doStage(r.manifest_url)}
                      disabled={busy === r.manifest_url}
                      style={{ padding: '4px 10px', fontSize: '11.5px', fontWeight: 600, borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', color: 'var(--text-primary)', cursor: 'pointer' }}
                    >
                      {busy === r.manifest_url ? 'Estagiando...' : 'Estagiar'}
                    </button>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>{r.description}</div>
                  {r.author_id && <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>autor: {r.author_id}</div>}
                </div>
              ))}
              {!searching && results.length === 0 && (
                <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Nenhum resultado. Confira a aba Registries se nada aparecer.</div>
              )}
            </div>
          )}

          {tab === 'estagiados' && (
            <div>
              {stagedError && <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '10px' }}>{stagedError}</div>}
              {staged.length === 0 && <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Nenhum plugin estagiado ainda.</div>}
              {staged.map(p => (
                <div key={p.name} style={{ border: '1px solid var(--border)', borderRadius: '8px', marginBottom: '8px', overflow: 'hidden' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 12px' }}>
                    <div>
                      <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>{p.name}</span>
                      <span style={{ fontSize: '11px', color: p.status === 'approved' ? '#4ade80' : 'var(--text-muted)', marginLeft: '8px' }}>{p.status}</span>
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      {p.status === 'staged' && (
                        <button onClick={() => toggleExpand(p.name)} style={{ padding: '4px 10px', fontSize: '11.5px', fontWeight: 600, borderRadius: '6px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', color: 'var(--text-primary)', cursor: 'pointer' }}>
                          {expanded === p.name ? 'Ocultar código' : 'Ver código'}
                        </button>
                      )}
                      {p.status === 'staged' && (
                        <button
                          onClick={() => doApprove(p.name)}
                          disabled={!viewed[p.name] || busy === p.name}
                          title={!viewed[p.name] ? 'Leia o código antes de aprovar' : undefined}
                          style={{ padding: '4px 10px', fontSize: '11.5px', fontWeight: 600, borderRadius: '6px', background: viewed[p.name] ? 'var(--accent)' : 'var(--bg-secondary)', color: viewed[p.name] ? '#fff' : 'var(--text-muted)', cursor: viewed[p.name] ? 'pointer' : 'not-allowed' }}
                        >
                          {busy === p.name ? 'Aprovando...' : 'Aprovar'}
                        </button>
                      )}
                    </div>
                  </div>
                  {expanded === p.name && (
                    <div style={{ padding: '0 12px 12px' }}>
                      <CodeBlock language="python">{code[p.name] ?? '# carregando...'}</CodeBlock>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {tab === 'registries' && <PluginRegistriesTab />}
          {tab === 'autores' && <PluginTrustedAuthorsTab />}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Commit (with Task 6's tab stubs, so the file still compiles)**

Since `PluginRegistriesTab` and `PluginTrustedAuthorsTab` are referenced above but written in Task 6, add temporary stubs now so the build is green at every commit:

```tsx
function PluginRegistriesTab() {
  return <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Carregando...</div>
}

function PluginTrustedAuthorsTab() {
  return <div style={{ fontSize: '12.5px', color: 'var(--text-muted)' }}>Carregando...</div>
}
```

Run: `cd frontend && npx tsc --noEmit` — must be clean.

```bash
git add frontend/components/Header.tsx
git commit -m "feat: modal do plugin marketplace - abas Buscar e Estagiados"
```

---

### Task 6: `PluginMarketplaceModal` — Registries + Autores confiáveis tabs

**Files:**
- Modify: `frontend/components/Header.tsx` — replace the two stub functions from Task 5 with real implementations

**Interfaces:**
- Consumes: `fetchPluginRegistries`, `addPluginRegistry`, `removePluginRegistry`, `fetchTrustedAuthors`, `trustPluginAuthor`, `untrustPluginAuthor`, `type TrustedAuthor` (Task 4).
- Produces: nothing consumed further — leaf components.

- [ ] **Step 1: Add the remaining imports**

Extend the import from Task 5 (Step 1) with the rest of the API functions:

```typescript
import {
  // ...
  fetchPluginRegistries, addPluginRegistry, removePluginRegistry,
  fetchTrustedAuthors, trustPluginAuthor, untrustPluginAuthor,
  type TrustedAuthor,
} from '../lib/api'
```

- [ ] **Step 2: Replace the `PluginRegistriesTab` stub**

```tsx
function PluginRegistriesTab() {
  const [registries, setRegistries] = useState<string[]>([])
  const [newUrl, setNewUrl] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const d = await fetchPluginRegistries()
      setRegistries(d.registries)
    } catch {
      setError('Erro ao carregar registries.')
    }
  }, [])

  useEffect(() => { load() }, [load])

  const add = async () => {
    if (!newUrl.trim()) return
    try {
      const d = await addPluginRegistry(newUrl.trim())
      setRegistries(d.registries)
      setNewUrl('')
    } catch {
      setError('Erro ao adicionar registry.')
    }
  }

  const remove = async (url: string) => {
    const d = await removePluginRegistry(url)
    setRegistries(d.registries)
  }

  return (
    <div>
      <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginBottom: '10px' }}>
        Registries adicionadas aqui ficam só em memória — não sobrevivem a um restart do backend. Pra deixar permanente, edite <code>PLUGIN_REGISTRY_URLS</code> em <code>config.py</code>.
      </div>
      {error && <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '10px' }}>{error}</div>}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        <input
          value={newUrl}
          onChange={e => setNewUrl(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') add() }}
          placeholder="https://... ou caminho local do registry.json"
          style={{ flex: 1, padding: '8px 10px', fontSize: '13px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)' }}
        />
        <button onClick={add} style={{ padding: '8px 14px', fontSize: '12.5px', fontWeight: 600, borderRadius: '8px', background: 'var(--accent)', color: '#fff', cursor: 'pointer' }}>Adicionar</button>
      </div>
      {registries.map(url => (
        <div key={url} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 10px', border: '1px solid var(--border)', borderRadius: '8px', marginBottom: '6px' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)', wordBreak: 'break-all' }}>{url}</span>
          <button onClick={() => remove(url)} style={{ color: 'var(--text-muted)', background: 'none', cursor: 'pointer', flexShrink: 0, marginLeft: '8px' }}><Trash2 size={13} /></button>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: Replace the `PluginTrustedAuthorsTab` stub**

```tsx
function PluginTrustedAuthorsTab() {
  const [authors, setAuthors] = useState<TrustedAuthor[]>([])
  const [authorId, setAuthorId] = useState('')
  const [pubkey, setPubkey] = useState('')
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      const d = await fetchTrustedAuthors()
      setAuthors(d.authors)
    } catch {
      setError('Erro ao carregar autores confiáveis.')
    }
  }, [])

  useEffect(() => { load() }, [load])

  const add = async () => {
    if (!authorId.trim() || !pubkey.trim()) return
    setError('')
    try {
      const d = await trustPluginAuthor(authorId.trim(), pubkey.trim())
      setAuthors(d.authors)
      setAuthorId('')
      setPubkey('')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erro ao confiar no autor — chave pública inválida?')
    }
  }

  const remove = async (id: string) => {
    const d = await untrustPluginAuthor(id)
    setAuthors(d.authors)
  }

  return (
    <div>
      <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginBottom: '10px' }}>
        A chave pública precisa vir de um canal que você confia (não do próprio manifest do plugin) — é o que impede um manifest malicioso de se autodeclarar confiável.
      </div>
      {error && <div style={{ color: '#f87171', fontSize: '12px', marginBottom: '10px' }}>{error}</div>}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
        <input value={authorId} onChange={e => setAuthorId(e.target.value)} placeholder="author_id"
          style={{ flex: '1 1 120px', padding: '8px 10px', fontSize: '13px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)' }} />
        <input value={pubkey} onChange={e => setPubkey(e.target.value)} placeholder="chave pública Ed25519 (hex)"
          style={{ flex: '2 1 220px', padding: '8px 10px', fontSize: '13px', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '8px', color: 'var(--text-primary)' }} />
        <button onClick={add} style={{ padding: '8px 14px', fontSize: '12.5px', fontWeight: 600, borderRadius: '8px', background: 'var(--accent)', color: '#fff', cursor: 'pointer' }}>Confiar</button>
      </div>
      {authors.map(a => (
        <div key={a.author_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 10px', border: '1px solid var(--border)', borderRadius: '8px', marginBottom: '6px' }}>
          <div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>{a.author_id}</div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', wordBreak: 'break-all' }}>{a.pubkey}</div>
          </div>
          <button onClick={() => remove(a.author_id)} style={{ color: 'var(--text-muted)', background: 'none', cursor: 'pointer', flexShrink: 0, marginLeft: '8px' }}><Trash2 size={13} /></button>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 4: Type-check and build**

Run: `cd frontend && npx tsc --noEmit && npm run build`
Expected: clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/components/Header.tsx
git commit -m "feat: modal do plugin marketplace - abas Registries e Autores confiaveis"
```

---

### Task 7: Live validation + CHANGELOG entry

**Files:**
- Modify: `CHANGELOG.md` — `## [Não lançado]` section (currently empty header, top of file after the v1.5 work closed)

No new source files. This task is manual verification + documentation, matching how every other feature in this project's history gets a changelog line only after it's been run for real (see `git log` — `docs:` commits documenting a feature always come after the `feat:` commit that shipped it, never before).

- [ ] **Step 1: Build and run the full app locally**

```bash
cd frontend && npm run build && cd ..
# Windows: duplo clique iniciar_frontend.bat (ou rode backend+frontend manualmente)
```

- [ ] **Step 2: Manual test with a real (self-hosted) registry**

This mirrors the "Critério de pronto" from the spec — no shortcuts, needs a real signed plugin to prove the whole chain end-to-end:

1. Generate a keypair: `python -c "import plugin_manager as pm; print(pm.generate_keypair())"` → note `(private_hex, public_hex)`.
2. Write a tiny plugin file, e.g. `C:\Users\User\Desktop\scratch\hello_plugin.py`:
   ```python
   def run(params: dict) -> str:
       return "hello from plugin"
   ```
3. Hash it: `python -c "import hashlib; print(hashlib.sha256(open('C:/Users/User/Desktop/scratch/hello_plugin.py','rb').read()).hexdigest())"`.
4. Sign it: `python -c "import plugin_manager as pm; print(pm.sign_payload('hello_plugin','1.0.0','<hash>','<private_hex>'))"`.
5. Write the manifest JSON (`code_url` pointing at a local `python -m http.server` serving the plugin file, or a `file://`-reachable path if `fetch_manifest`/`stage` support it — check `stage()`'s `requests.get` call; if it requires `http(s)://`, run `python -m http.server 8899` in the scratch folder).
6. Write a registry JSON containing one entry pointing at that manifest URL.
7. In the UI: Plugin Marketplace → Registries tab → add the registry (local file path or `http://localhost:8899/registry.json`) → Buscar tab → search → Estagiar → Estagiados tab → Ver código (confirm it shows `hello_plugin.py`'s real content) → Aprovar (button should have been disabled until "Ver código" was clicked — confirm that) → confirm status flips to `approved`.
8. Confirm `plugins/hello_plugin.py` exists on disk after approval.
9. Autores confiáveis tab: confirm the author_id used above shows up (it was trusted via CLI in step 4's prerequisite — actually trust it via the UI instead, to test that path: `Autores confiáveis` tab → enter the author_id + public_hex → Confiar → re-run the search/stage/approve flow above end-to-end through the UI only, no `plugin_manager.trust_author()` call from Python).
10. Try approving a plugin from an author NOT trusted, or a manifest with a tampered `code_sha256` — confirm the UI shows the real `PluginError` text ("HASH NÃO BATE" / "AUTOR NÃO CONFIADO"), not a generic error.

- [ ] **Step 3: Update CHANGELOG**

```markdown
## [Não lançado]

- Plugin Marketplace UI — `stage`/`approve`/busca de registries/gestão de
  autores confiáveis agora acessíveis pelo frontend (antes só via
  `plugin_manager.py` no terminal). Endpoints de escrita (`stage`/`approve`/
  `trust`) atrás da mesma senha do `/export/data` — decisão documentada na
  spec, ver `docs/superpowers/specs/2026-08-04-plugin-marketplace-ui-design.md`.
  Registries também podem ser adicionadas em runtime (sem restart), mesmo
  padrão do `SPECIALIST_MODELS` override.
```

- [ ] **Step 4: Commit**

```bash
git add CHANGELOG.md
git commit -m "docs: registra Plugin Marketplace UI no changelog"
```
