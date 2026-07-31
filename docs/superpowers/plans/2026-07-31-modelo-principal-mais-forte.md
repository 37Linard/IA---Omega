# Modelo principal mais forte — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar o modelo principal do agente (`OLLAMA_MODEL`) de `qwen2.5:7b-instruct-q3_K_M` pra um candidato de classe ~14B, validado contra golden tasks, mantendo 100% local.

**Architecture:** Nenhuma nova — reusa o split `OLLAMA_MODEL`/`FALLBACK_MODEL`/`ENSEMBLE_MODELS`/`MANAGER_MODEL` já existente em `config.py` e `llm.py`. É troca de valor de config + validação, com um ajuste de robustez (timeout de geração configurável, hoje hardcoded baixo demais pra modelo maior/mais lento).

**Tech Stack:** Python 3.11 (ambiente de dev) — projeto real roda com `C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe` (não usar `.venv/`, incompleto). Ollama local. pytest.

## Global Constraints

- 100% local — sem chamada a API externa de LLM.
- Prioridade confirmada: qualidade > velocidade (offload parcial CPU/RAM aceitável).
- Hardware real: RTX 2060 **6GB VRAM** (budget autorizado pro modelo: até 4GB), RAM total 16GB.
- `OLLAMA_MAX_LOADED_MODELS=1` — só 1 modelo residente na VRAM por vez (não mexer, fora de escopo).
- `config.py` é **gitignored** (`.gitignore:35`) — mudanças nele NÃO entram em commit; só `config.example.py`, código e testes vão pro git.
- Não reabrir `SPECIALIST_MODELS_ENABLED` (já desligado por thrashing documentado em `config.py:171-178`) nem mudar `NUM_CTX`/`NUM_PREDICT`/`FALLBACK_MODEL` — fora de escopo (ver spec).
- Spec completa: `docs/superpowers/specs/2026-07-31-modelo-principal-mais-forte-design.md`.

---

### Task 1: Timeout de geração configurável em `llm.py`

Hoje `_request()` usa `timeout=120` hardcoded em duas chamadas `requests.post`
(`llm.py:105` e `llm.py:113`). Modelo maior com offload parcial pra RAM gera
mais devagar — 120s pode não bastar pra `NUM_PREDICT=700` tokens, disparando
retry/fallback por lentidão (não por travamento real). Extrai isso pra
`GENERATE_TIMEOUT` em `config.py`, com valor inicial mais folgado.

**Files:**
- Modify: `config.py` (adiciona `GENERATE_TIMEOUT` perto de `NUM_PREDICT`/`NUM_CTX`, linha ~41)
- Modify: `config.example.py` (mesma adição, mirror — linha ~71, mantém padrão do arquivo)
- Modify: `llm.py:6` (import), `llm.py:105`, `llm.py:113` (usa a constante em vez de `120`)
- Test: `tests/test_llm_fallback.py`

**Interfaces:**
- Produces: `config.GENERATE_TIMEOUT: int` (segundos) — consumido só dentro de `llm.py`, nenhuma outra task depende disso além de ler o valor.

- [ ] **Step 1: Escrever o teste que falha**

Adicionar em `tests/test_llm_fallback.py` (mesmo arquivo, mesmo padrão de
`fake_post` já usado nos outros testes do arquivo):

```python
def test_generate_uses_configured_timeout(monkeypatch):
    # llm.py importa GENERATE_TIMEOUT por valor (from config import ...) —
    # patchar o nome já importado em llm_mod, não o atributo em config_mod.
    monkeypatch.setattr(llm_mod, "GENERATE_TIMEOUT", 300)

    captured_timeouts = []

    def fake_post(url, json=None, timeout=None, **kw):
        captured_timeouts.append(timeout)
        return _fake_response(200, _stats_payload("ok"))

    monkeypatch.setattr(llm_mod.requests, "post", fake_post)

    OllamaLLM(model="qwen2.5:7b", fallback_model="").generate("oi")

    assert captured_timeouts == [300]
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest tests/test_llm_fallback.py::test_generate_uses_configured_timeout -v`
Expected: FAIL — `captured_timeouts == [120]` (valor hardcoded atual), não `[300]`.

- [ ] **Step 3: Adicionar `GENERATE_TIMEOUT` em `config.py`**

Em `config.py`, logo abaixo da linha `KEEP_ALIVE = "30m"` (linha 44):

```python
GENERATE_TIMEOUT  = 300    # segundos máx por chamada de geração — modelo maior
                            # com offload parcial pra RAM demora mais que os
                            # 120s de antes; 300s dá folga sem mascarar travamento real
```

E o mesmo bloco em `config.example.py`, logo abaixo de `KEEP_ALIVE` (linha 74):

```python
GENERATE_TIMEOUT  = 300    # segundos máx por chamada de geração (aumente se seu
                            # modelo for grande/lento com offload parcial pra RAM)
```

- [ ] **Step 4: Usar a constante em `llm.py`**

`llm.py:6`, adicionar `GENERATE_TIMEOUT` no import existente:

```python
from config import OLLAMA_URL, NUM_PREDICT, NUM_CTX, NUM_GPU, TEMPERATURE, VISION_MODEL, KEEP_ALIVE, FALLBACK_MODEL, GENERATE_TIMEOUT
```

`llm.py:105`, trocar:

```python
            response = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=GENERATE_TIMEOUT)
```

`llm.py:113`, trocar:

```python
        with requests.post(f"{self.base_url}/api/generate", json=payload, stream=True, timeout=GENERATE_TIMEOUT) as response:
```

- [ ] **Step 5: Rodar o teste e confirmar que passa**

Run: `C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest tests/test_llm_fallback.py -v`
Expected: PASS — todos os testes do arquivo, incluindo o novo.

- [ ] **Step 6: Commit**

`config.py` é gitignored — não entra no `git add`.

```bash
git add config.example.py llm.py tests/test_llm_fallback.py
git commit -m "feat: timeout de geracao configuravel (GENERATE_TIMEOUT), prep pra modelo maior"
```

---

### Task 2: Escolher, baixar e validar modelo candidato via `eval_harness.py`

Task operacional — sem mudança de código. Usa o suporte que `eval_harness.py`
já tem (`--model`, `eval_harness.py:113`) pra rodar golden tasks contra o
candidato SEM tocar em `config.py` ainda, comparando com o baseline atual.

**Files:** nenhum criado/modificado (validação pura).

**Interfaces:**
- Consumes: `eval_harness.py --model <tag>` (já existe), `GOLDEN_TASKS` de `eval/golden_tasks.py` (5 tasks: `conversational_greeting`, `python_arithmetic`, `currency_routing_not_crypto`, `crypto_routing_not_currency`, `compound_task_multi_domain_regression`).
- Produces: decisão (seguir pra Task 3 com tag X, ou tentar quant mais agressivo, ou abortar) — registrada no commit da Task 3, não em arquivo separado.

- [ ] **Step 1: Rodar baseline (modelo atual, 7B)**

Run: `C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe eval_harness.py`
Anotar do output: `X/5 passou`, tempo (`elapsed`) de cada task.

- [ ] **Step 2: Baixar o candidato**

Candidato inicial: `qwen2.5:14b-instruct-q4_K_M` (mesma família do modelo
atual, já validada nesse projeto pra tool-calling; ~9GB, quant Q4_K_M).

Run: `ollama pull qwen2.5:14b-instruct-q4_K_M`

Se esse tag específico não existir na biblioteca do Ollama no momento (nomes
mudam), rodar `ollama search qwen2.5` ou checar ollama.com/library/qwen2.5 e
escolher a variante 14B-instruct de quant mais próximo de Q4_K_M disponível.

- [ ] **Step 3: Rodar eval com o candidato, observando VRAM**

Run: `C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe eval_harness.py --model qwen2.5:14b-instruct-q4_K_M`

Em paralelo (outro terminal), observar offload: `nvidia-smi` durante o run,
ou o dashboard já existente do projeto (`/metrics`, HealthModal — badge de
VRAM). Anotar `X/5 passou` e tempo de cada task.

- [ ] **Step 4: Decidir**

Comparar com o baseline do Step 1:

- **Candidato passa >= mesma quantidade de golden tasks que o baseline** →
  seguir pra Task 3 com essa tag.
- **Candidato passa menos tasks** (modelo maior não necessariamente acerta
  mais em tarefas de tool-calling/formato estrito — vale checar) → tentar
  1x com `qwen2.5:14b-instruct-q5_K_M` (mais fiel, mais pesado) OU aceitar
  que o ganho não compensa e abortar o plano nessa task, reportar ao usuário.
- **Tempo por task inviável** (ex.: >3-4x o baseline, resposta demora
  minutos) mesmo passando as tasks → tentar `qwen2.5:14b-instruct-q3_K_M`
  (mais leve, menos VRAM/RAM) antes de desistir do tamanho 14B.

Não há teste automatizado pra esse passo — é leitura de output + julgamento
contra os critérios acima. Registrar a tag final escolhida pra usar na Task 3.

---

### Task 3: Trocar `OLLAMA_MODEL` pro candidato validado, sincronizar `ENSEMBLE_MODELS`

`ENSEMBLE_MODELS` (`config.py:11`) é lista literal, não referencia
`OLLAMA_MODEL` dinamicamente — trocar só o principal e esquecer de
`ENSEMBLE_MODELS[0]` deixa o self-consistency votando entre o modelo novo
forte e uma string desatualizada do 7B antigo. Um teste de consistência
pega esse erro caso se repita no futuro.

**Files:**
- Modify: `config.py:7` (`OLLAMA_MODEL`), `config.py:11` (`ENSEMBLE_MODELS[0]`)
- Test: `tests/test_config_model_consistency.py` (novo)

**Interfaces:**
- Consumes: tag escolhida na Task 2 (ex.: `qwen2.5:14b-instruct-q4_K_M`).
- Produces: `config.OLLAMA_MODEL` novo valor, consumido por `llm.py`/`agent.py`/`orchestrator.py` (nenhuma mudança de assinatura, só o valor da string).

- [ ] **Step 1: Trocar `OLLAMA_MODEL` em `config.py` (SEM mexer em `ENSEMBLE_MODELS` ainda)**

`config.py:7`, trocar o valor (mantendo o comentário histórico e acrescentando
a entrada nova):

```python
OLLAMA_MODEL   = "qwen2.5:14b-instruct-q4_K_M"   # trocado de qwen2.5:7b-instruct-q3_K_M (2026-07-31) — usuario pediu modelo mais forte, prioridade qualidade>velocidade confirmada. Validado com eval_harness.py contra baseline 7B antes da troca (ver docs/superpowers/plans/2026-07-31-modelo-principal-mais-forte.md, Task 2). Historico: llama3.2:3b (antes de 2026-07-04) ignorava instrucao, repetia tool call; qwen2.5:7b Q4_K_M nao cabia 100% em 6GB, Q3_K_M cabia
```

- [ ] **Step 2: Escrever o teste que falha**

Criar `tests/test_config_model_consistency.py`:

```python
import config


def test_primary_model_and_ensemble_first_slot_match():
    """ENSEMBLE_MODELS[0] eh string literal, nao referencia OLLAMA_MODEL —
    trocar o principal sem atualizar este slot deixa o self-consistency
    votando entre o modelo novo e uma versao desatualizada do antigo."""
    assert config.ENSEMBLE_MODELS[0] == config.OLLAMA_MODEL


def test_fallback_model_never_in_ensemble_pool():
    if config.FALLBACK_MODEL:
        assert config.FALLBACK_MODEL not in config.ENSEMBLE_MODELS
```

(A segunda função já é garantida por `tests/test_agent_ensemble.py:402` em
outro arquivo — repetida aqui só como guarda-local barata contra a mesma
classe de erro; não é duplicação de intenção, é o mesmo invariante visto de
dois arquivos que evoluem em momentos diferentes.)

- [ ] **Step 3: Rodar o teste e confirmar que falha**

Run: `C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest tests/test_config_model_consistency.py -v`
Expected: FAIL em `test_primary_model_and_ensemble_first_slot_match` —
`ENSEMBLE_MODELS[0]` ainda é `"qwen2.5:7b-instruct-q3_K_M"`, `OLLAMA_MODEL`
já é o novo.

- [ ] **Step 4: Sincronizar `ENSEMBLE_MODELS`**

`config.py:11`:

```python
ENSEMBLE_MODELS = ["qwen2.5:14b-instruct-q4_K_M", "llama3.1:8b"]  # pool do ensemble multi-modelo (self-consistency troca de modelo entre tentativas em vez de só reamostrar o mesmo). NUNCA incluir llama3.2:3b aqui — já é o FALLBACK_MODEL de infra, tem histórico de "ignorava instrução, repetia tool call" (ver comentário do OLLAMA_MODEL acima), arriscaria vencer voto de qualidade com resposta confiante e errada.
```

- [ ] **Step 5: Rodar o teste e confirmar que passa**

Run: `C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest tests/test_config_model_consistency.py -v`
Expected: PASS — as duas funções.

- [ ] **Step 6: Commit**

`config.py` é gitignored — só o teste novo entra no git.

```bash
git add tests/test_config_model_consistency.py
git commit -m "test: garante OLLAMA_MODEL e ENSEMBLE_MODELS[0] sincronizados"
```

---

### Task 4: Regressão completa + validação ao vivo

**Files:** nenhum (validação).

**Interfaces:**
- Consumes: tudo das Tasks 1-3 já commitado/editado.
- Produces: confirmação final de que a troca não quebrou nada e funciona na prática.

- [ ] **Step 1: Rodar a suite completa**

Run: `C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest`
Expected: todos os testes passam (baseline era 148+ passing antes desta
sessão; agora +2 testes novos das Tasks 1 e 3, nenhuma regressão nos
demais — a suite é toda mockada, não depende do modelo real estar de pé).

- [ ] **Step 2: Checar se o servidor já está rodando (achado operacional recorrente neste projeto: reload automático às vezes trava servindo código velho)**

Run: `netstat -ano | grep :8000`

Se tiver PID: `taskkill /PID <pid> /F` (e o correspondente da porta 3000, se
o frontend também estiver de pé) antes de relançar, pra garantir que o
código atualizado (Task 1's `GENERATE_TIMEOUT`) está realmente servindo.

- [ ] **Step 3: Subir o app e rodar 2-3 tarefas reais**

Duplo clique em `iniciar_frontend.bat` (backend 8000 + frontend 3000),
abrir `http://localhost:3000`. Rodar 2-3 prompts reais — de preferência os
que o usuário já sentiu "fracos" antes, ou uma das golden tasks
(`compound_task_multi_domain_regression` é a mais exigente).

Conferir:
- Resposta faz sentido / é melhor que a percepção anterior do 7B.
- Dashboard de performance (botão ❤️, `/metrics`) mostra o modelo novo
  carregado, TPS e uso de VRAM/contexto.
- Nenhum fallback espúrio pro `llama3.2:3b` só por lentidão (checar
  `/trace/llm/recent` ou log — `fallback_used=True` não deveria aparecer
  em uso normal, só se o Ollama travar de verdade).

- [ ] **Step 4: Reverter se não compensar**

Se a lentidão for inviável na prática mesmo com a prioridade
qualidade>velocidade confirmada: voltar `OLLAMA_MODEL` e
`ENSEMBLE_MODELS[0]` em `config.py` pro valor antigo
(`qwen2.5:7b-instruct-q3_K_M`) — mudança de 1 arquivo gitignored, sem
impacto em nenhum commit já feito. As Tasks 1 e 3 (timeout configurável,
teste de sincronismo) continuam válidas e úteis independente da decisão
final do modelo.

- [ ] **Step 5: Commit final (se mantido)**

Nenhum arquivo novo pra commitar aqui além do que já foi commitado nas
Tasks 1 e 3 (a troca em si vive só em `config.py`, gitignored). Esse step é
só confirmação — não há `git add`/`git commit` a rodar.
