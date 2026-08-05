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

**Decisão de segurança (revisada em brainstorm):** `plugin_manager.py` hoje
documenta que instalação é "SEMPRE uma ação manual do operador... nunca algo
que o agente decide sozinho em runtime" e que por isso `stage`/`approve`/
`trust_author` nunca ficam alcançáveis por rede — só CLI. Expor isso via API
muda esse invariante (ainda mais com Tailscale ligado desde v1.5). Decisão:
expor mesmo assim, mas travar os 3 endpoints de escrita atrás de
`Depends(check_auth)` — mesma senha (`AUTH_PASSWORD`) que já protege
`/export/data`. O agente continua sem acesso (rota HTTP não é tool
carregada por `tool_loader.py`, nem nunca foi) — o que muda é só "alcançável
sem estar no terminal da máquina", não "alcançável pelo agente/prompt
injection". Resíduo de risco: quem tem a senha remota já tem acesso amplo
à API mesmo (audit log, export de dados, terminal tool etc.), então isso
não abre uma categoria nova de exposição, só estende uma já aceita.
`plugin_manager.py` (docstring no topo) precisa de uma linha atualizada
documentando que a API agora existe como segunda via, com a mesma trava de
senha.

Endpoints novos:

- `GET /plugins/registries` — lista `PLUGIN_REGISTRY_URLS` (config) + as
  adicionadas em runtime. Leitura, sem auth extra (mesmo padrão de
  `/specialist-models` GET).
- `POST /plugins/registries {url}` / `DELETE /plugins/registries/{url}` —
  override em memória (`_runtime_registries: list[str]`, mesmo padrão do
  `_runtime_models`), não persiste. Rate-limit (`Depends(_check_rate_limit)`),
  sem `check_auth` (só edita uma lista de URLs a consultar, não instala nada).
- `GET /plugins/search?q=...` — chama `search_registries(q)`. Leitura.
- `POST /plugins/stage {manifest_url}` — chama `stage()` — **`check_auth` +
  rate limit**. Retorna nome + erro claro se hash/assinatura falhar
  (mensagem do `PluginError` já é boa).
- `GET /plugins/staged` — `list_staged()`. Leitura.
- `GET /plugins/staged/{name}/code` — lê `plugins/{name}.staged.py` e
  devolve como texto (reusa `_safe_name` do `plugin_manager.py` pro path).
  Leitura.
- `POST /plugins/approve {name}` — `approve()` — **`check_auth` + rate
  limit**.
- `GET /plugins/trusted-authors` — leitura.
- `POST /plugins/trust {author_id, pubkey}` / `DELETE
  /plugins/trust/{author_id}` — **`check_auth` + rate limit** (decide em
  quem confiar é decisão tão sensível quanto aprovar um plugin).

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
