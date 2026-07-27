# Ensemble Multi-Modelo Real — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Quando o self-consistency existente dispara uma reescrita (score de reflection abaixo do threshold), as tentativas seguintes devem rodar em modelos DIFERENTES (não só reamostrar o mesmo modelo), e o crítico que dá a nota deve sempre usar o modelo principal — não o modelo da tentativa corrente.

**Architecture:** `ReActAgent` guarda o LLM original em `self._primary_llm` no início de `run()`. No loop de self-consistency já existente (`agent.py`, tratamento de `Final Answer`), quando uma reescrita é necessária, `self.llm` é trocado para o próximo modelo de `config.ENSEMBLE_MODELS` (índice cíclico) antes de continuar o loop. `_reflect()` (o crítico) passa a chamar sempre `self._primary_llm`, nunca `self.llm` corrente. Depois de esgotar as tentativas, `self.llm` é restaurado pro principal antes do voto holístico (`_vote_best_answer`).

**Tech Stack:** Python, Ollama (via `llm.OllamaLLM`), pytest.

## Global Constraints

- Pool de modelos: `ENSEMBLE_MODELS = ["qwen2.5:7b-instruct-q3_K_M", "llama3.1:8b"]` — exatamente esses 2, `llama3.2:3b` NUNCA entra no pool de voto (é `FALLBACK_MODEL` de infraestrutura, não crítico de qualidade).
- `config.py` e `config.example.py` devem ficar em sincronia — este projeto já teve bugs reais de nomes faltando em `config.example.py` (ver `git log`, achado de CI em 2026-07-23). Toda config nova entra nos DOIS arquivos.
- Nenhuma UI nova — só um campo `model` a mais no evento `reflection` que já existe.
- Suite completa (`pytest` na raiz, usa o Python real do projeto, não `.venv/`) deve continuar 100% verde — nenhuma regressão em `tests/test_self_consistency.py`.

---

### Task 1: Config — pool de modelos do ensemble

**Files:**
- Modify: `config.py:10-11`
- Modify: `config.example.py:28-29`
- Test: nenhum teste dedicado (é config estática) — validado indiretamente pelo Task 2.

**Interfaces:**
- Produces: `config.ENSEMBLE_MODELS: list[str]` — consumido pelo Task 2.

- [ ] **Step 1: Adicionar `ENSEMBLE_MODELS` em `config.py`**

Em `config.py`, logo depois da linha 10 (`FALLBACK_MODEL = ...`) e antes da linha 11 (`API_URL = ...`), adicionar:

```python
ENSEMBLE_MODELS = ["qwen2.5:7b-instruct-q3_K_M", "llama3.1:8b"]  # pool do ensemble multi-modelo (self-consistency troca de modelo entre tentativas em vez de só reamostrar o mesmo). NUNCA incluir llama3.2:3b aqui — já é o FALLBACK_MODEL de infra, tem histórico de "ignorava instrução, repetia tool call" (ver comentário do OLLAMA_MODEL acima), arriscaria vencer voto de qualidade com resposta confiante e errada.
```

- [ ] **Step 2: Adicionar o mesmo em `config.example.py`**

Em `config.example.py`, logo depois da linha 28 (`FALLBACK_MODEL = ...`), adicionar:

```python
ENSEMBLE_MODELS = ["qwen2.5:7b-instruct-q3_K_M", "llama3.1:8b"]  # pool do ensemble multi-modelo — ver config.py pra explicação completa
```

- [ ] **Step 3: Verificar que os dois arquivos importam sem erro**

Run: `python -c "from config import ENSEMBLE_MODELS; print(ENSEMBLE_MODELS)"`
Expected: `['qwen2.5:7b-instruct-q3_K_M', 'llama3.1:8b']`

- [ ] **Step 4: Commit**

```bash
git add config.py config.example.py
git commit -m "feat: adiciona ENSEMBLE_MODELS pra pool do ensemble multi-modelo"
```

---

### Task 2: Mecanismo de troca de modelo no self-consistency

**Files:**
- Modify: `agent.py:16` (import de config)
- Modify: `agent.py` (novo import de `OllamaLLM` no topo)
- Modify: `agent.py:819` (guarda `self._primary_llm`)
- Modify: `agent.py:1010` (candidato ganha nome do modelo)
- Modify: `agent.py:1013-1026` (troca de modelo antes do retry)
- Modify: `agent.py:1028-1030` (restaura `self.llm` antes do voto + unpack de 3-tupla)
- Modify: `agent.py:529-555` (`_vote_best_answer` — unpack de 3-tupla)
- Modify: `tests/test_self_consistency.py` (mocka `OllamaLLM` nos testes que disparam retry — achado do pre-flight scan, ver Step 11)
- Test: `tests/test_agent_ensemble.py` (novo)

**Interfaces:**
- Consumes: `config.ENSEMBLE_MODELS` (Task 1), `llm.OllamaLLM(model: str)` (já existe, construtor barato sem estado de conexão).
- Produces: `self._primary_llm` (referência ao LLM principal da sessão, usado pelo Task 3); `self._reflection_candidates: list[tuple[int, str, str]]` (score, resposta, nome_do_modelo) — Task 3 depende deste formato de 3-tupla.

- [ ] **Step 1: Escrever o teste que falha — 2ª tentativa usa o modelo alternativo**

Criar `tests/test_agent_ensemble.py`:

```python
import threading

import agent as agent_mod
from agent import ReActAgent


class _StubMemory:
    def get_context(self, task="", session_id=""):
        return ""

    def save_session_with_llm(self, *a, **k):
        pass


class _StubProfile:
    def observe_message(self, text):
        pass

    def increment_interactions(self):
        pass

    def get_system_context(self):
        return ""


class _ScriptedLLM:
    """Mesmo estilo de tests/test_self_consistency.py — distingue a chamada
    pelo conteúdo do prompt (ReAct/reflection/voto)."""

    def __init__(self, model, react_responses=None, reflect_jsons=None, vote_responses=None):
        self.model = model
        self.react_responses = list(react_responses or [])
        self.reflect_jsons = list(reflect_jsons or [])
        self.vote_responses = list(vote_responses or [])

    def generate(self, prompt, on_token=None):
        if "Avalie se a resposta" in prompt:
            return self.reflect_jsons.pop(0)
        if "Candidatos de resposta" in prompt:
            return self.vote_responses.pop(0)
        resp = self.react_responses.pop(0)
        if on_token:
            for ch in resp:
                on_token(ch)
        return resp


def _bare_agent(llm):
    a = ReActAgent.__new__(ReActAgent)
    a.llm                = llm
    a.tools              = {}
    a.memory             = _StubMemory()
    a.profile            = _StubProfile()
    a._cancel            = threading.Event()
    a._cancel_reason     = "usuário"
    a.conversation       = []
    a.specialist_context = ""
    a.session_id         = ""
    a._emit              = None
    return a


TASK = "escreva um resumo curto"  # mesmo task-sentinel de test_self_consistency.py


def test_second_attempt_uses_ensemble_alternate_model(monkeypatch):
    monkeypatch.setattr(agent_mod, "REFLECTION_ENABLED", True)
    monkeypatch.setattr(agent_mod, "REFLECTION_THRESHOLD", 4)
    monkeypatch.setattr(agent_mod, "SELF_CONSISTENCY_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(agent_mod, "ENSEMBLE_MODELS", ["primary-model", "alt-model"])

    primary_llm = _ScriptedLLM(
        model="primary-model",
        react_responses=["Thought: 1.\nFinal Answer: tentativa 1 (principal)"],
        reflect_jsons=[
            '{"score": 2, "issues": [], "hint": ""}',
            '{"score": 5, "issues": [], "hint": ""}',
        ],
        vote_responses=["1"],
    )
    alt_llm = _ScriptedLLM(
        model="alt-model",
        react_responses=["Thought: 2.\nFinal Answer: tentativa 2 (alternativo)"],
    )

    constructed_models = []

    def fake_ollama_llm(model):
        constructed_models.append(model)
        assert model == "alt-model"  # só o alternativo deveria ser construído
        return alt_llm

    monkeypatch.setattr(agent_mod, "OllamaLLM", fake_ollama_llm)

    a = _bare_agent(primary_llm)
    result = a.run(TASK, step_callback=None)

    assert constructed_models == ["alt-model"]
    assert result == "tentativa 2 (alternativo)"
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python -m pytest tests/test_agent_ensemble.py -v`
Expected: FAIL — `self.llm` nunca é trocado hoje, `constructed_models` fica `[]` (nunca chama `OllamaLLM`), e a resposta final é a tentativa 1 reamostrada (não existe reamostragem real hoje sem troca de modelo, então o teste falha por `AssertionError` em `constructed_models == ["alt-model"]` ou por `IndexError` ao faltar `react_responses` do `primary_llm` pra 2ª tentativa).

- [ ] **Step 3: Importar `OllamaLLM` e `ENSEMBLE_MODELS` em `agent.py`**

Em `agent.py`, adicionar logo abaixo da linha 16 (import de `config`):

```python
from config import ENSEMBLE_MODELS
from llm import OllamaLLM
```

- [ ] **Step 4: Guardar o LLM principal no início de `run()`**

Em `agent.py:819`, mudar:

```python
        self._reflection_candidates = []   # [(score, answer), ...] — self-consistency (ensemble/voto)
```

para:

```python
        self._reflection_candidates = []   # [(score, answer, model), ...] — self-consistency (ensemble/voto)
        self._primary_llm = self.llm       # modelo principal da sessão — self.llm pode trocar durante o ensemble, isso nunca muda
```

- [ ] **Step 5: Candidato passa a guardar o nome do modelo**

Em `agent.py:1010`, mudar:

```python
                    self._reflection_candidates.append((score, action_input))
```

para:

```python
                    self._reflection_candidates.append((score, action_input, self.llm.model))
```

- [ ] **Step 6: Trocar de modelo antes de retry**

Em `agent.py:1013-1026`, o bloco atual é:

```python
                    if score < REFLECTION_THRESHOLD and can_retry:
                        # Streaming já emitiu tokens — reseta conteúdo no frontend
                        if _fs[0]:
                            emit({"type": "reset_content", "content": ""})
                        retry_hint = (
                            f"Thought: Minha resposta foi avaliada com score {score}/5 (minimo={REFLECTION_THRESHOLD}).\n"
                            + (f"Problemas: {'; '.join(issues)}\n" if issues else "")
                            + (f"Como melhorar: {hint}\n" if hint else "")
                            + "Vou reescrever a Final Answer de forma mais completa e precisa.\n"
                        )
                        self.scratchpad.append(retry_hint)
                        log.info("REFLECTION: reescrevendo resposta (tentativa %d/%d)...",
                                  len(self._reflection_candidates) + 1, SELF_CONSISTENCY_MAX_ATTEMPTS)
                        continue
```

Mudar para (adiciona a troca de modelo logo antes do `continue`):

```python
                    if score < REFLECTION_THRESHOLD and can_retry:
                        # Streaming já emitiu tokens — reseta conteúdo no frontend
                        if _fs[0]:
                            emit({"type": "reset_content", "content": ""})
                        retry_hint = (
                            f"Thought: Minha resposta foi avaliada com score {score}/5 (minimo={REFLECTION_THRESHOLD}).\n"
                            + (f"Problemas: {'; '.join(issues)}\n" if issues else "")
                            + (f"Como melhorar: {hint}\n" if hint else "")
                            + "Vou reescrever a Final Answer de forma mais completa e precisa.\n"
                        )
                        self.scratchpad.append(retry_hint)
                        next_model = ENSEMBLE_MODELS[len(self._reflection_candidates) % len(ENSEMBLE_MODELS)]
                        self.llm = OllamaLLM(model=next_model)
                        log.info("REFLECTION: reescrevendo resposta (tentativa %d/%d) com modelo '%s'...",
                                  len(self._reflection_candidates) + 1, SELF_CONSISTENCY_MAX_ATTEMPTS, next_model)
                        continue
```

- [ ] **Step 7: Restaurar `self.llm` antes do voto + ajustar unpack de 3-tupla**

Em `agent.py:1028-1030`, o bloco atual é:

```python
                    if len(self._reflection_candidates) > 1:
                        winner_idx = self._vote_best_answer(task, self._reflection_candidates)
                        winner_score, winner_answer = self._reflection_candidates[winner_idx]
```

Mudar para:

```python
                    self.llm = self._primary_llm  # restaura o principal antes do voto e de qualquer turno seguinte
                    if len(self._reflection_candidates) > 1:
                        winner_idx = self._vote_best_answer(task, self._reflection_candidates)
                        winner_score, winner_answer, _winner_model = self._reflection_candidates[winner_idx]
```

- [ ] **Step 8: Ajustar `_vote_best_answer` pra 3-tupla**

Em `agent.py:529-555`, a assinatura e o unpack mudam de `list[tuple[int, str]]` / `for i, (_, ans) in enumerate(candidates)` para `list[tuple[int, str, str]]` / `for i, (_, ans, _model) in enumerate(candidates)`:

```python
    def _vote_best_answer(self, task: str, candidates: list[tuple[int, str, str]]) -> int:
        """Vota entre candidatos de Final Answer coletados (self-consistency real:
        N tentativas independentes, não 2 sequenciais). Julgamento holístico — o
        LLM vê todos os candidatos juntos e escolhe — em vez de só comparar
        scores calculados isoladamente um contra o outro em chamadas separadas
        de _reflect (mais ruidoso: nada garante que o critic calibra igual entre
        chamadas) ou aceitar a reescrita mais recente às cegas."""
        if len(candidates) <= 1:
            return 0
        options = "\n".join(f"[{i}] {ans[:400]}" for i, (_, ans, _model) in enumerate(candidates))
```

(o resto do método não muda — só a linha da assinatura e a linha do `options`).

- [ ] **Step 9: Rodar o teste e confirmar que passa**

Run: `python -m pytest tests/test_agent_ensemble.py -v`
Expected: PASS

- [ ] **Step 10: Rodar a suite de self-consistency e confirmar a quebra esperada (achado do pre-flight)**

Run: `python -m pytest tests/test_self_consistency.py -v`
Expected: FAIL em várias — esses testes disparam retry (score abaixo do threshold) sem mockar `OllamaLLM`. Depois do Step 6/7, o retry agora chama `self.llm = OllamaLLM(model=next_model)` de verdade, substituindo o `_ScriptedLLM` do teste por um `OllamaLLM` real — a próxima chamada de `generate()` tentaria rede de verdade e falharia/travaria. Isso é esperado neste ponto; corrigido no próximo step.

- [ ] **Step 11: Corrigir `tests/test_self_consistency.py` pra mockar `OllamaLLM` nos testes que disparam retry**

Em `tests/test_self_consistency.py`, adicionar `import agent as agent_mod` já existe no topo do arquivo. Em CADA teste abaixo (todos já recebem `monkeypatch` como parâmetro), adicionar a linha `monkeypatch.setattr(agent_mod, "OllamaLLM", lambda model: llm)` logo depois da construção de `llm = _ScriptedLLM(...)` e antes de `a = _bare_agent(llm)` — isso faz o retry "trocar de modelo" pra o MESMO objeto `_ScriptedLLM` (a troca de modelo em si não é o que esses testes verificam, então reusar o mesmo stub preserva o comportamento scripted original):

- `test_self_consistency_keeps_first_answer_when_vote_picks_it`
- `test_reflection_recorded_in_tracing_for_dashboard`
- `test_self_consistency_keeps_second_answer_when_vote_picks_it`
- `test_vote_overrides_naive_max_score_pick`
- `test_self_consistency_votes_among_three_independent_attempts`
- `test_self_consistency_guards_first_answer_against_ignored_tool_error`

Exemplo (primeiro teste do arquivo), muda de:

```python
    llm = _ScriptedLLM(
        react_responses=[
            "Thought: pronto.\nFinal Answer: resposta A",
            "Thought: reescrevendo.\nFinal Answer: resposta B (reescrita, mas pior)",
        ],
        reflect_jsons=[
            '{"score": 3, "issues": ["faltou contexto"], "hint": "adicione contexto"}',
            '{"score": 2, "issues": [], "hint": ""}',
        ],
        vote_responses=["0"],  # o juiz (holístico) escolhe o índice 0 -- resposta A
    )
    a = _bare_agent(llm)
```

para:

```python
    llm = _ScriptedLLM(
        react_responses=[
            "Thought: pronto.\nFinal Answer: resposta A",
            "Thought: reescrevendo.\nFinal Answer: resposta B (reescrita, mas pior)",
        ],
        reflect_jsons=[
            '{"score": 3, "issues": ["faltou contexto"], "hint": "adicione contexto"}',
            '{"score": 2, "issues": [], "hint": ""}',
        ],
        vote_responses=["0"],  # o juiz (holístico) escolhe o índice 0 -- resposta A
    )
    monkeypatch.setattr(agent_mod, "OllamaLLM", lambda model: llm)
    a = _bare_agent(llm)
```

Aplicar o mesmo padrão (adicionar a linha `monkeypatch.setattr(agent_mod, "OllamaLLM", lambda model: llm)` entre a construção de `llm` e a construção de `a`) nos outros 5 testes listados acima. `test_no_retry_when_first_score_already_passes_threshold` NÃO precisa da mudança — score já passa no threshold na 1ª tentativa, `self.llm` nunca é trocado nesse teste.

- [ ] **Step 12: Rodar a suite de self-consistency de novo e confirmar que passa**

Run: `python -m pytest tests/test_self_consistency.py -v`
Expected: PASS em todos

- [ ] **Step 13: Commit**

```bash
git add agent.py tests/test_agent_ensemble.py tests/test_self_consistency.py
git commit -m "feat: self-consistency troca de modelo real entre tentativas (ensemble)"
```

---

### Task 3: Crítico (`_reflect`) sempre usa o modelo principal

**Files:**
- Modify: `agent.py:516`
- Test: `tests/test_agent_ensemble.py` (adiciona teste)

**Interfaces:**
- Consumes: `self._primary_llm` (Task 2).

- [ ] **Step 1: Escrever o teste que falha**

Adicionar em `tests/test_agent_ensemble.py`:

```python
def test_reflect_always_uses_primary_llm_not_current_attempt_model(monkeypatch):
    monkeypatch.setattr(agent_mod, "REFLECTION_ENABLED", True)
    monkeypatch.setattr(agent_mod, "REFLECTION_THRESHOLD", 4)
    monkeypatch.setattr(agent_mod, "SELF_CONSISTENCY_MAX_ATTEMPTS", 2)
    monkeypatch.setattr(agent_mod, "ENSEMBLE_MODELS", ["primary-model", "alt-model"])

    primary_llm = _ScriptedLLM(
        model="primary-model",
        react_responses=["Thought: 1.\nFinal Answer: tentativa 1 (principal)"],
        # As DUAS avaliações de reflection devem vir do primary -- mesmo a que
        # avalia a resposta gerada pelo modelo alternativo.
        reflect_jsons=[
            '{"score": 2, "issues": [], "hint": ""}',
            '{"score": 5, "issues": [], "hint": ""}',
        ],
        vote_responses=["1"],
    )
    alt_llm = _ScriptedLLM(
        model="alt-model",
        react_responses=["Thought: 2.\nFinal Answer: tentativa 2 (alternativo)"],
        reflect_jsons=[],  # vazio de propósito: se _reflect chamar isto, IndexError (pop de lista vazia)
    )

    monkeypatch.setattr(agent_mod, "OllamaLLM", lambda model: alt_llm)

    a = _bare_agent(primary_llm)
    result = a.run(TASK, step_callback=None)

    assert result == "tentativa 2 (alternativo)"
    assert alt_llm.reflect_jsons == []  # nunca foi tocado -- prova que _reflect nunca usou o alt_llm
    assert primary_llm.reflect_jsons == []  # as 2 avaliações vieram todas do primary
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python -m pytest tests/test_agent_ensemble.py::test_reflect_always_uses_primary_llm_not_current_attempt_model -v`
Expected: FAIL com `IndexError: pop from empty list` (prova que hoje `_reflect` usa `self.llm`, que na 2ª tentativa é o `alt_llm` cujo `reflect_jsons` está vazio de propósito).

- [ ] **Step 3: Mudar `_reflect` pra usar `self._primary_llm`**

Em `agent.py:516`, mudar:

```python
            raw   = self.llm.generate(prompt)
```

para (dentro de `_reflect`, único ponto de chamada de LLM nesse método):

```python
            raw   = self._primary_llm.generate(prompt)
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `python -m pytest tests/test_agent_ensemble.py -v`
Expected: PASS (todos os testes do arquivo)

- [ ] **Step 5: Commit**

```bash
git add agent.py tests/test_agent_ensemble.py
git commit -m "fix: _reflect sempre usa o modelo principal, nunca o modelo da tentativa corrente"
```

---

### Task 4: Observabilidade — nome do modelo no evento `reflection`

**Files:**
- Modify: `agent.py:1002-1007` (1º emit de reflection)
- Modify: `agent.py:1031-1039` (emit do resultado do voto)
- Test: `tests/test_agent_ensemble.py` (adiciona teste)

**Interfaces:**
- Consumes: `self._reflection_candidates` no formato 3-tupla (Task 2).
- Produces: evento `reflection` com campo `model` opcional — consumido pelo frontend existente (que já ignora campos desconhecidos em eventos, nenhuma mudança de frontend necessária nesta tarefa).

- [ ] **Step 1: Escrever o teste que falha**

Adicionar em `tests/test_agent_ensemble.py`:

```python
def test_reflection_event_includes_model_name(monkeypatch):
    monkeypatch.setattr(agent_mod, "REFLECTION_ENABLED", True)
    monkeypatch.setattr(agent_mod, "REFLECTION_THRESHOLD", 3)
    monkeypatch.setattr(agent_mod, "SELF_CONSISTENCY_MAX_ATTEMPTS", 2)

    primary_llm = _ScriptedLLM(
        model="primary-model",
        react_responses=["Thought: pronto.\nFinal Answer: resposta boa de primeira"],
        reflect_jsons=['{"score": 4, "issues": [], "hint": ""}'],
    )
    events = []
    a = _bare_agent(primary_llm)

    a.run(TASK, step_callback=lambda ev: events.append(ev))

    reflection_events = [e for e in events if e["type"] == "reflection"]
    assert len(reflection_events) == 1
    assert reflection_events[0]["model"] == "primary-model"
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `python -m pytest tests/test_agent_ensemble.py::test_reflection_event_includes_model_name -v`
Expected: FAIL com `KeyError: 'model'`

- [ ] **Step 3: Adicionar `model` no 1º emit de reflection**

Em `agent.py:1002-1007`, mudar:

```python
                    emit({
                        "type":     "reflection",
                        "content":  rc,
                        "score":    score,
                        "accepted": score >= REFLECTION_THRESHOLD,
                    })
```

para:

```python
                    emit({
                        "type":     "reflection",
                        "content":  rc,
                        "score":    score,
                        "accepted": score >= REFLECTION_THRESHOLD,
                        "model":    self.llm.model,
                    })
```

- [ ] **Step 4: Adicionar `model` no emit do resultado do voto**

Em `agent.py:1031-1039`, mudar:

```python
                        emit({
                            "type":    "reflection",
                            "content": (
                                f"Self-consistency: {len(self._reflection_candidates)} tentativas, "
                                f"voto escolheu a nº{winner_idx + 1} (score {winner_score}/5)"
                            ),
                            "score":    winner_score,
                            "accepted": True,
                        })
```

para:

```python
                        emit({
                            "type":    "reflection",
                            "content": (
                                f"Self-consistency: {len(self._reflection_candidates)} tentativas, "
                                f"voto escolheu a nº{winner_idx + 1} (score {winner_score}/5)"
                            ),
                            "score":    winner_score,
                            "accepted": True,
                            "model":    _winner_model,
                        })
```

- [ ] **Step 5: Rodar o teste e confirmar que passa**

Run: `python -m pytest tests/test_agent_ensemble.py -v`
Expected: PASS (todos)

- [ ] **Step 6: Rodar a suite completa**

Run: `python -m pytest`
Expected: todos os testes passam (nenhuma regressão em `test_self_consistency.py` ou no resto da suite)

- [ ] **Step 7: Commit**

```bash
git add agent.py tests/test_agent_ensemble.py
git commit -m "feat: evento reflection ganha campo model pra observabilidade do ensemble"
```

---

### Task 5: Validação ao vivo com `eval_harness.py`

**Files:**
- Nenhum arquivo de produção modificado — só validação manual.

**Interfaces:**
- Consumes: `eval_harness.py` (já existe), `config.REFLECTION_THRESHOLD`.

- [ ] **Step 1: Confirmar que `llama3.1:8b` está disponível no Ollama local**

Run: `ollama list`
Expected: a linha `llama3.1:8b` aparece na lista (já confirmado presente antes desta sessão — se não aparecer, rodar `ollama pull llama3.1:8b` primeiro).

- [ ] **Step 2: Subir `REFLECTION_THRESHOLD` temporariamente pra forçar o ensemble disparar**

Em `config.py`, trocar temporariamente (NÃO commitar esta mudança):

```python
REFLECTION_THRESHOLD = 5  # temporário — força quase toda Final Answer a reescrever, valida o ensemble ao vivo
```

- [ ] **Step 3: Rodar uma golden task com log em nível INFO**

Run: `python eval_harness.py --task python_arithmetic`
Expected: no output, aparecer pelo menos uma linha `REFLECTION: reescrevendo resposta (tentativa 2/3) com modelo 'llama3.1:8b'...` — confirma que a troca de modelo aconteceu de verdade (não só em teste mockado) e que o Ollama local conseguiu carregar `llama3.1:8b` sem erro.

- [ ] **Step 4: Confirmar que a tarefa ainda passa (PASS) apesar da troca de modelo**

Verificar no output final: `1/1 passou`. Se falhar, investigar se `llama3.1:8b` respondeu em formato ReAct incompatível (thought/action) — não esperado, mas é a hipótese nº1 se a golden task quebrar só com o threshold subido.

- [ ] **Step 5: Reverter `REFLECTION_THRESHOLD`**

Em `config.py`, reverter pro valor original (checar `git diff config.py` pra confirmar que a única mudança pendente era essa linha, depois `git checkout -- config.py` ou editar de volta manualmente).

Run: `git diff config.py`
Expected: sem diferenças (arquivo igual ao commit anterior)

- [ ] **Step 6: Rodar a suite completa uma última vez**

Run: `python -m pytest`
Expected: todos os testes passam

---

## Self-Review (preenchido durante a escrita do plano)

- **Cobertura do spec**: pool de modelos (Task 1) ✓, mecanismo de troca (Task 2) ✓, crítico sempre no principal (Task 3) ✓, observabilidade do campo `model` (Task 4) ✓, validação ao vivo com eval_harness (Task 5) ✓. Tratamento de erro (fallback automático do `OllamaLLM.generate`) não precisa de tarefa própria — já é comportamento herdado, mencionado no spec como "nenhum tratamento novo necessário".
- **Placeholders**: nenhum "TBD"/"implementar depois" — todo código de cada step está completo e citável.
- **Consistência de tipos**: `self._reflection_candidates` é `list[tuple[int, str, str]]` desde o Task 2 (Step 5) em diante, usado de forma consistente em `_vote_best_answer` (Task 2, Step 8), no restore do winner (Task 2, Step 7) e no emit do Task 4 (`_winner_model`). `ENSEMBLE_MODELS` é `list[str]`, consumido só em `agent.py` (Task 2, Step 6).
