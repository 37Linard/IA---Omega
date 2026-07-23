# Changelog

Histórico de versões do agente. Formato livre, não segue semver estrito — cada
bloco é uma sessão/leva de trabalho, não um release numerado à parte.

## [Não lançado] — 2026-07-23 — hardening de segurança

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

### Adicionado
- `audit.py`/`tracing.py`: `prune(max_age_days)` — sem isso `audit.db`/`traces.db`
  cresciam pra sempre. Endpoints `POST /audit/prune`, `POST /trace/llm/prune`.
- `DISCORD_WEBHOOK_URL` configurada e testada em produção.
- `OLLAMA_MAX_LOADED_MODELS=1` / `OLLAMA_NUM_PARALLEL=1`.
- 40+ testes novos cobrindo os achados acima. Suite completa: 197 passed.

## v1.4 — 2026-07-22

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
