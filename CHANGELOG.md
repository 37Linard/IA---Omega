# Changelog

Histórico de versões do agente. Formato livre, não segue semver estrito — cada
bloco é uma sessão/leva de trabalho, não um release numerado à parte.

## [Não lançado]

Trabalho commitado em `main` desde v1.4, ainda sem número de versão atribuído
(escopo grande demais pra resumir aqui sem virar a própria reconciliação de novo —
ver [[project_agente_ia]] na memória do agente pra changelog sessão-a-sessão):
RAG re-rank com cross-encoder, sandbox local real via Job Object (Windows), eval
noturno automático (golden tasks 1x/dia), self-consistency N=3 com votação real,
streaming de tool-call parcial, ensemble multi-modelo real (troca de modelo entre
tentativas), Prometheus/Grafana, plugin signing Ed25519 + marketplace discovery,
unificação de `knowledge_graph.json` em `agent_memory.json`, POC de LoRA fine-tune
(isolado em `lora_experiments/`, não é produto).

## v1.4 — 2026-07-23 — hardening de segurança

### Corrigido
- **Sandbox `terminal`**: whitelist só olhava a 1ª palavra do comando, mas rodava com
  `shell=True` — `echo oi && del /f /q ...` passava reto. Bloqueia agora qualquer
  metacaractere de encadeamento (`&`, `|`, `;`, `` ` ``, `$(`, `>`, `<`).
- **Sandbox `git`**: bloqueio de `-f`/`--force` era substring ingênuo, bypassado por
  flag curta combinada (`git branch -Df`). Trocado por `shlex.split` + check por token.
- **`keyboard`/`mouse`**: sem whitelist possível (controle bruto de tecla/clique) —
  travam sempre via HITL agora, mesmo com `HITL_ENABLED=False` global.
- **`browser`**: SSRF — só validava `url.startswith("http")`, deixava navegar pra
  localhost/IP privado/LAN. Bloqueia loopback/private/link-local/`.local`.
- **`google_drive`**: query da API montada por f-string sem escapar `'` — termo de
  busca injetava cláusula extra, burlando filtro de mimeType/trashed.
- **`generate_image`**: disputa de VRAM com Ollama na GPU (RTX 2060 6GB) — descarrega
  o Ollama antes de gerar imagem, recarrega sozinho no próximo request.
- **Sandbox `run_python`**: WASM (stdlib puro) sempre rodava primeiro e "sucedia"
  mesmo faltando lib (numpy/pandas), nunca cedendo pro Docker — imagem `ia-sandbox`
  ficava inalcançável. Agora tenta Docker se WASM falhar por `ModuleNotFoundError`.
- **`sandbox.Dockerfile`**: build quebrado — `python:3.12-slim` atualizou e já reserva
  UID/GID 65534 (nobody/nogroup), `useradd`/`groupadd` batiam em "already exists".
- `KEEP_ALIVE` faltando em `config.example.py` (drift do template real).
- **`config.example.py`**: 10 nomes faltando vs `config.py` real (`API_URL`,
  `EMBED_MODEL`, `MANAGER_MODEL`, `REDIS_URL`, `REFLECTION_ENABLED`,
  `REFLECTION_THRESHOLD`, `SHORT_TERM_MSGS`, `SHORT_TERM_TTL`, `SPECIALIST_MODELS`,
  `link_note_in_conversas_index`) — qualquer clone novo seguindo o próprio README
  (`cp config.example.py config.py`) quebrava com `ImportError`. Achado rodando o CI.
- **CI (`pyautogui`)**: conecta em X server na importação, não só no uso — quebrava
  em Linux headless mesmo com `.screenshot` mockado. Fix: módulo falso injetado em
  `sys.modules` antes do import lazy, real nunca é tocado.
- Vazamento de conexão sqlite em caminhos de erro (`audit.py`, `tracing.py`,
  `run_sql_tool.py` — mesmo bug em 3 arquivos).
- `tools/_paths.py` (novo): boundary check de pasta permitida usava `startswith()`
  puro — `"Desktop-secret/x"` passava como se estivesse dentro de `"Desktop/"`.
- `run_sql_tool`: bloqueio de `DROP`/`TRUNCATE` exigia espaço literal,
  `"DROP\nTABLE x"` bypassava (mesma classe do bug do `git_tool` acima).
- `slack_tool`: `list_channels` — descrição da tool citava o método, código nunca
  implementava.
- `api.py`: `POST /model` chamava `log.info()` com `log` nunca definido —
  `NameError` toda troca de modelo pela API, sempre quebrado, sem teste cobrindo.
  Achado pelo mypy.

### Adicionado
- `audit.py`/`tracing.py`: `prune(max_age_days)` — sem isso `audit.db`/`traces.db`
  cresciam pra sempre. Endpoints `POST /audit/prune`, `POST /trace/llm/prune`.
- `DISCORD_WEBHOOK_URL` configurada e testada em produção.
- `OLLAMA_MAX_LOADED_MODELS=1` / `OLLAMA_NUM_PARALLEL=1`.
- CI (GitHub Actions) — `pytest` a cada push/PR pro `main`.
- Secret-scanning (`gitleaks`) no CI, rodado também local contra o histórico
  completo de commits (0 achado).
- `requirements.txt` com versão pinada em 35 libs (era 0); 6 libs listadas mas
  não instaladas de fato no ambiente real, instaladas.
- `pytest-cov` — cobertura real medida (33%→41% ao longo da sessão).
- 73 testes novos cobrindo tools de leitura/escrita sem cobertura nenhuma
  (`run_sql`, `read_spreadsheet`, `generate_chart`, `generate_report`, `save_note`,
  `remember_fact`, `http_request`, `clipboard`, `screenshot`, `analyze_image`,
  `read_file`, `list_directory`).
- Circuit breaker: cooldown por tool (`CIRCUIT_BREAKER_COOLDOWNS`) — credencial
  faltando (Drive/Notion/Slack/Discord/email) = 30min, rede transiente
  (web_search/fetch_page/get_currency/get_crypto) = 90s, em vez de 300s fixo pra tudo.
- Dashboard: taxa de reflection-rewrite (quanto o critic reprova a 1ª resposta).
- mypy configurado (`mypy.ini`, lenient — projeto começou sem tipagem nenhuma).
- `/health` avisa quando `JWT_SECRET` vazio com `AUTH_PASSWORD` ativa.
- 60+ testes novos no total cobrindo os achados acima. Suite completa: 291 passed.

## v1.3.1 — 2026-07-22

- `rag_search` busca também episódios de memória (resumo de sessões passadas).
- Fix real: memória não era compartilhada entre orchestrator e especialistas —
  episódios nunca eram criados em produção.
- Guard de self-consistency também no branch "1ª tentativa ganhou".
- `workspace/` movido pra fora da árvore vigiada pelo reload do uvicorn (NTFS junction).
- Otimização de performance medida: `OLLAMA_FLASH_ATTENTION=1` + `OLLAMA_KV_CACHE_TYPE=q8_0`
  + troca de modelo (Q4_K_M → Q3_K_M) pra caber 100% na GPU de 6GB.

## v1.3 — 2026-07-20/21 — segurança em camadas e observabilidade

- Testes automatizados (pytest) do zero.
- HITL por tier de risco (`read`/`write`/`destructive`) em vez de lista fixa de tools.
- Isolamento por especialista em tarefa multi-domínio (least privilege).
- Guard de prompt-injection (`wrap_untrusted`) em tools que ingerem conteúdo externo.
- Fallback automático de modelo (`FALLBACK_MODEL`) se o principal travar/timeout.
- Schema por tool — rejeita input malformado antes de executar.
- Self-consistency (best-of-2) na reflection.
- Tracing estruturado (span por LLM-call) + circuit breaker por tool.
- Dashboard consolidado (`/metrics`) + alertas de erro/circuito aberto.
- Git hook `pre-push` — roda golden tasks antes de subir código.
- Memória episódica cross-sessão (recall da conversa anterior).
- Plan-then-Execute persistido em disco.
- Execução proativa — agente cria suas próprias tarefas agendadas via chat.
- Guard de fidelidade da resposta final (Final Answer que ignora erro real da Observation).
- `config.py` removido do controle de versão (repo é público).

## v1.2 — 2026-07-05

- Refino visual do frontend.
- Fontes de pesquisa ao vivo no chat.
- `generate_image` com seed/múltiplas imagens/upscale.

## v1.1 — 2026-07-01/04

- Workflow DAG (visualização do plano multi-especialista).
- Fix de robustez multi-domínio (detecção de tarefa composta).
- Geração de imagem local (Stable Diffusion / sd-turbo).
- Migração ChromaDB → LanceDB.
- Auth (JWT) / Audit log / Rate limiting.
- Plugin manager sandboxado.

## v1.0 — 2026-06-24/27 — primeira versão completa

- Arquitetura ReAct + Plan-then-Execute + auto-correção.
- Tiered Memory (short-term + facts + knowledge graph).
- Reflection Loop (crítico avalia a própria resposta).
- Multi-model (specialists paralelos).
- Docker Sandbox pro `run_python`.
- Pipeline visual de browser (screenshot + VLM).
- Dashboard de performance + Human-in-the-Loop.
- Frontend Next.js completo (substituiu HTML/JS).
