# Plugin Marketplace UI — v1.6

## Contexto

`plugin_manager.py` já tem o fluxo completo de descoberta/instalação de plugins
de terceiros: `search_registries()`, `fetch_manifest()`, `stage()` (baixa +
valida hash + assinatura Ed25519), `list_staged()`, `approve()` (só move
`.staged.py` → `.py`, depois de humano ler o código), `list_trusted_authors()`
/ `trust_author()` / `untrust_author()`. Nada disso está exposto em `api.py`
nem no frontend — só dá pra usar chamando as funções direto em Python. Registro
de origens (`PLUGIN_REGISTRY_URLS`) é lista fixa em `config.py`, vazia por
padrão, só editável reiniciando o processo.

## Objetivo

Expor esse fluxo via API + modal no frontend, mantendo a mesma garantia de
segurança que já existe no `plugin_manager.py`: **stage** é sempre automático
(hash+assinatura já protegem), **approve** exige que o operador tenha visto o
código antes — a UI não pode virar um botão "instalar" de 1 clique sem review.

## Não-objetivos

- Não mexe na execução (`run_plugin`, sandbox WASM) — já existe e não muda.
- Não adiciona registry pública própria — usuário continua trazendo a URL.
- Sem persistência em disco pra registries adicionadas via UI (mesmo padrão
  já usado por `SPECIALIST_MODELS` runtime override em `orchestrator.py`:
  fica em memória, reseta no restart, documentado).

## Design

### Backend (`api.py`)

Novos endpoints, todos atrás do mesmo `AUTH_PASSWORD`/JWT que já protege o
resto da API (nada novo em auth):

- `GET /plugins/registries` — lista `PLUGIN_REGISTRY_URLS` (config) + as
  adicionadas em runtime.
- `POST /plugins/registries {url}` / `DELETE /plugins/registries/{url}` —
  override em memória (`_runtime_registries: list[str]`, mesmo padrão do
  `_runtime_models`), não persiste.
- `GET /plugins/search?q=...` — chama `search_registries(q)`.
- `POST /plugins/stage {manifest_url}` — chama `stage()`, retorna nome +
  erro claro se hash/assinatura falhar (mensagem do `PluginError` já é boa).
- `GET /plugins/staged` — `list_staged()`.
- `GET /plugins/staged/{name}/code` — lê `plugins/{name}.staged.py` e
  devolve como texto (reusa `_safe_name` do `plugin_manager.py` pro path).
- `POST /plugins/approve {name}` — `approve()`.
- `GET /plugins/trusted-authors` / `POST /plugins/trust {author_id, pubkey}`
  / `DELETE /plugins/trust/{author_id}`.

Todos os erros de `PluginError` viram HTTP 400 com a mensagem original —
já são mensagens pensadas pro humano ler (ex: "HASH NÃO BATE...").

### Frontend

Modal novo (`PluginMarketplaceModal.tsx`), botão `Puzzle` (lucide) no
`Header.tsx` — mesmo padrão dos outros modais (RAG, Specialist Models).

Abas dentro do modal:

1. **Buscar** — input de busca + lista de resultados (nome/versão/autor/
   descrição) vindos das registries configuradas. Botão "Estagiar" por
   resultado → chama stage, resultado some da busca e aparece em "Estagiados".
2. **Estagiados** — lista com status (staged/approved). Item staged expande
   pra mostrar o código (`<pre>` com highlight, reusa o componente de code
   block do chat) — **botão "Aprovar" só habilita depois do usuário abrir/
   expandir o código** (estado local `hasViewedCode`, força o review antes
   do clique valer).
3. **Registries** — lista as configuradas, campo pra adicionar uma nova em
   runtime (com aviso "não sobrevive a restart, edite config.py pra
   permanente"), botão remover.
4. **Autores confiáveis** — lista/adiciona/remove pubkey por author_id
   (necessário pra assinatura passar em `_verify_signature`).

Erros de `PluginError` (hash/assinatura errada) aparecem como banner
vermelho no modal, texto exato que a API devolveu.

### Testes

- `tests/test_api_plugins.py` — endpoints novos, mock de `plugin_manager`
  (não bate rede real). Cobre: stage com hash errado → 400, approve sem
  stage prévio → 400, runtime registries add/remove/list.
- Sem teste E2E novo (Playwright) — mock de rede pra registry externa foge
  do padrão dos E2E existentes (browser real + WS real, sem mock de rede).

## Critério de pronto

- `pytest` verde com os testes novos.
- `npm run build` do frontend limpo (TS).
- Testado ao vivo com uma registry real (usuário monta um manifest de
  teste, roda `generate_keypair()` + `sign_payload()` pra assinar, sobe
  num servidor HTTP local simples) — busca → stage → vê código → aprova →
  `list_staged()` mostra `approved`.
