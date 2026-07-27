# Ensemble multi-modelo real

## Contexto

O agente já tem self-consistency (commit `09b9b23`): quando a `Final Answer` recebe
score baixo de `_reflect()` (< `REFLECTION_THRESHOLD`), o agente reamostra até
`SELF_CONSISTENCY_MAX_ATTEMPTS` (default 3) vezes e vota holisticamente
(`_vote_best_answer`) entre os candidatos coletados. Hoje todas as tentativas usam
o MESMO modelo (`self.llm`, tipicamente `qwen2.5:7b-instruct-q3_K_M`) — é
resampling, não ensemble de verdade.

Objetivo: quando o self-consistency dispara, as tentativas seguintes devem vir de
modelos DIFERENTES (não só reamostrar o mesmo), pra reduzir o viés/erro
característico de um modelo específico.

**Restrição de hardware**: RTX 2060 6GB, `OLLAMA_MAX_LOADED_MODELS=1` — só um
modelo cabe carregado por vez. "Ensemble simultâneo" não é viável; o design é
sequencial (cada troca de modelo custa unload+reload, já é um custo tolerado hoje
em outros caminhos do sistema — fallback de modelo, specialists).

## Decisões (da sessão de brainstorming)

- **Objetivo**: mais precisão/robustez em tarefas difíceis (não é sobre custo/latência).
- **Gatilho**: reaproveita o gatilho existente do self-consistency (score de
  reflection abaixo do threshold) — sem custo extra em tarefas que já passam de
  primeira. Não dispara sempre, não é opt-in manual.
- **Pool de modelos**: `qwen2.5:7b-instruct-q3_K_M` (atual/principal) +
  `llama3.1:8b` (arquitetura diferente, diversidade real). `llama3.2:3b`
  DELIBERADAMENTE excluído do pool de voto — já tem histórico ruim neste projeto
  (era o modelo principal antes de 2026-07-04, trocado por "ignorava instrução,
  repetia tool call"); seu papel já definido é `FALLBACK_MODEL` de infraestrutura
  (Ollama travou/timeout), não deveria também competir por voto de qualidade —
  arrisca vencer com uma resposta confiante e errada.

## Arquitetura / mecanismo

- `config.py`: `ENSEMBLE_MODELS = [OLLAMA_MODEL, "llama3.1:8b"]` — lista, fácil
  estender/testar outro modelo depois sem mexer em código.
- `ReActAgent.run()`: guarda `self._primary_llm = self.llm` logo no início (antes
  do loop ReAct) — referência estável ao modelo principal da sessão.
- No bloco de self-consistency (`agent.py`, dentro do tratamento de `Final Answer`,
  ~linhas 986-1047): quando `score < REFLECTION_THRESHOLD and can_retry`, ANTES do
  `continue`, troca `self.llm` para `ENSEMBLE_MODELS[len(self._reflection_candidates) % len(ENSEMBLE_MODELS)]`
  (índice cíclico baseado em quantas tentativas já foram feitas) — a tentativa
  seguinte roda de fato num modelo diferente, via `OllamaLLM(model=nome)` novo
  (construção é barata, sem estado persistente de conexão).
- `_reflect()` passa a receber/usar sempre `self._primary_llm.generate` (não
  `self.llm.generate` da tentativa corrente) — mesma razão que já levou o voto a
  ser holístico em vez de comparar scores isolados: crítico calibrando diferente
  entre chamadas já era ruidoso com o MESMO modelo; ficaria pior com modelos
  diferentes julgando.
- Ao esgotar tentativas (`can_retry` vira falso) ou aceitar de primeira: restaura
  `self.llm = self._primary_llm` ANTES de `_vote_best_answer` — o juiz do voto
  final e qualquer turno seguinte da mesma sessão sempre usam o modelo principal,
  nunca ficam "presos" no alternativo.
- `self._reflection_candidates`: item passa de `(score, resposta)` para
  `(score, resposta, nome_do_modelo)`. O evento `reflection` emitido pro frontend
  ganha campo opcional `model` — só observabilidade (o painel de reflection já
  existe no frontend, é só mais um campo no mesmo evento), sem UI nova.
- `_vote_best_answer` não muda de comportamento (continua holístico, usa
  `self.llm.generate` — que nesse ponto já foi restaurado pro principal).

## Tratamento de erro

Nenhum tratamento novo necessário: `OllamaLLM.generate()` já tem retry +
fallback pro `FALLBACK_MODEL` embutido (herdado de graça) se `llama3.1:8b`
falhar ao responder. `llama3.1:8b` já está confirmado presente (`ollama list`),
não precisa de pull.

## Testes / validação

- `tests/test_agent_ensemble.py` (novo, mock): força reflection a devolver score
  baixo repetidamente, confirma que (a) a 2ª tentativa usa `llama3.1:8b` de
  verdade (via nome do modelo no candidato), (b) `_reflect` sempre chamou
  `_primary_llm` independente de qual modelo gerou a tentativa, (c) `self.llm`
  volta a ser o principal depois do voto.
- Validação ao vivo: sobe `REFLECTION_THRESHOLD` temporariamente (força quase
  toda tarefa entrar em retry) e roda `eval_harness.py` numa golden task, confere
  no log que a troca de modelo realmente aconteceu (`ORCHESTRATOR`/log de model
  usado) e que a resposta final faz sentido. Reverte o threshold depois.
- Suite completa (`pytest`) deve continuar passando — não deve haver regressão em
  `test_self_consistency.py`.

## Fora de escopo (explicitamente não incluído)

- Ensemble simultâneo (2+ modelos carregados ao mesmo tempo) — inviável no
  hardware atual (6GB VRAM).
- UI nova para visualizar o ensemble (além do campo `model` no evento
  `reflection` já existente).
- Expandir `ENSEMBLE_MODELS` além de 2 entradas, ou reincluir `llama3.2:3b` no
  pool de voto — decisão explícita da sessão de brainstorming, revisitar só se
  o usuário pedir depois de ver resultado real.
