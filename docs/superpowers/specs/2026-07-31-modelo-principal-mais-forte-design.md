# Modelo principal mais forte (troca de OLLAMA_MODEL)

## Contexto

Agente roda 100% local, hoje em `qwen2.5:7b-instruct-q3_K_M` (config.py:7).
Usuário quer o agente "mais forte" (mais capacidade de raciocínio/instrução),
mantendo 100% local — sem depender de API externa.

**Restrição de hardware real** (não a que memória antiga registrava — corrigido
nesta sessão): RTX 2060 **6GB VRAM** (confirmado pelo comentário em
`config.py:7`, que documenta Q4_K_M do 7B não coube 100% em 6GB, só Q3_K_M
coube). Usuário autorizou usar até **4GB de VRAM** pro modelo (não os 6GB
inteiros — sobra de propósito pra SO/display). RAM total: 16GB. Prioridade
confirmada: **qualidade > velocidade** — offload parcial CPU/RAM é aceitável
mesmo deixando a resposta mais lenta.

`OLLAMA_MAX_LOADED_MODELS=1` está setado nessa mesma GPU — só um modelo residente
por vez (relevante pro approach descartado abaixo, não pro escolhido).

## Approach descartado: modelo por especialista (SPECIALIST_MODELS)

Já avaliado e **explicitamente desligado** em `config.py:178`
(`SPECIALIST_MODELS_ENABLED = False`) por achado de 2026-07-23: com só 1 modelo
residente na VRAM por vez, trocar de modelo por especialista força
descarrega/recarrega a cada chamada (thrashing) — piora performance na RTX 2060
6GB em vez de melhorar. Não reconsiderado aqui; só faz sentido com GPU 16GB+
(`OLLAMA_MAX_LOADED_MODELS>1`), fora do escopo desta mudança.

## Decisão

Trocar só o **modelo principal** (`OLLAMA_MODEL`) por um modelo de classe
maior (~14B, quantizado), mantendo toda a arquitetura ReAct/self-consistency/
ensemble/fallback como está — é troca de config + validação, não rework.

## Componentes afetados

- **`config.py:7` (`OLLAMA_MODEL`)**: novo modelo, classe 14B, quantização
  escolhida por teste real de VRAM (ver "Processo de escolha" abaixo) — mesmo
  método que levou o 7B de Q4_K_M pra Q3_K_M (`eval_harness.py` + observação
  de % de GPU usado).
- **`config.py:11` (`ENSEMBLE_MODELS`)**: é lista literal, não referencia
  `OLLAMA_MODEL` dinamicamente — `ENSEMBLE_MODELS[0]` precisa ser atualizado
  em conjunto pra não ficar apontando pro 7B antigo enquanto o principal já
  mudou (ficaria com voto entre modelo novo forte + string desatualizada do
  7B antigo, quebrando a intenção do ensemble). `llama3.1:8b` (índice 1,
  diversidade de arquitetura) continua sem mudança.
- **`FALLBACK_MODEL`** (`llama3.2:3b`): sem mudança — rede de segurança de
  infraestrutura (travou/timeout), independente do tamanho do modelo principal.
- **`MANAGER_MODEL`**: sem mudança (vazio = herda `OLLAMA_MODEL`) — routing/
  classificação também fica mais forte de brinde; se isso pesar demais na
  latência de decisões simples, é um ajuste separado, fora de escopo aqui.
- **Timeout/retry em `llm.py`** (`MAX_RETRIES`/timeout de geração — checar
  valor atual no arquivo antes de mexer): modelo maior gera mais devagar,
  principalmente com offload parcial pra RAM. Se o timeout atual foi calibrado
  pro 7B, um 14B mais lento pode disparar `FALLBACK_MODEL` só por lentidão, não
  por travamento real — ajustar o valor se a validação ao vivo mostrar isso.
- **`NUM_CTX`/`NUM_PREDICT`**: sem mudança — não é o problema relatado, fora
  de escopo (YAGNI).

## Processo de escolha do modelo/quant

Sem acesso a benchmark ao vivo desta sessão, a escolha final do tag exato
(nome+quant) acontece na implementação, não travada aqui:

1. Checar `ollama list` (modelos já baixados) e a biblioteca do Ollama por
   opções atuais na família Qwen2.5-Instruct classe 14B (mesma família do
   modelo atual — já validada nesse projeto pra tool-calling).
2. Testar quant candidato (começar por Q4_K_M) rodando o agente e observando
   `nvidia-smi`/dashboard de performance já existente (`/metrics`, HealthModal)
   — mesmo método usado pra decidir Q3_K_M do 7B.
3. Se não coube com qualidade aceitável de resposta nem com offload pra RAM
   (16GB) em tempo tolerável, descer pra quant mais agressivo (Q3_K_M) antes
   de descer de tamanho (14B→7B maior quant seria desistir do objetivo).

## Tratamento de erro

Nenhum mecanismo novo — reusa o que já existe e já foi testado:
`FALLBACK_MODEL` cobre timeout/travamento (`llm.py`), ensemble cobre score
baixo de reflection trocando pra `llama3.1:8b` na 2ª tentativa. Único ajuste
possível é recalibrar o valor do timeout (ver acima), não a lógica.

## Testes / validação

- `eval_harness.py` contra golden tasks: rodar baseline atual (7B, registrar
  taxa de sucesso/tempo) vs candidato (14B) antes de considerar a troca
  definitiva — mesmo processo já usado pra validar a troca de quant do 7B.
- Suite `pytest` (148+ testes, mockada) deve continuar passando sem alteração
  — não valida o modelo em si, só a lógica em volta.
- Validação ao vivo: 2-3 tarefas reais que hoje "sentem fracas" (se o usuário
  tiver exemplos concretos, usar esses; senão, tarefas multi-domínio do
  `golden_tasks.py`), conferir resposta + tempo percebido.
- Reverter fácil: `OLLAMA_MODEL` (e `ENSEMBLE_MODELS[0]`) voltam pro valor
  atual se a validação não compensar (velocidade inviável mesmo com
  prioridade em qualidade).

## Fora de escopo

- Approach B (modelo por especialista) — já avaliado e rejeitado por hardware
  (thrashing), não reaberto aqui.
- Approach C (split pensar/agir com modelo de raciocínio dedicado) — mais
  engenharia nova, não pedido nesta rodada; revisitar só se a troca simples
  de modelo não for suficiente.
- Mudar `NUM_CTX`/`NUM_PREDICT`.
- Trocar `FALLBACK_MODEL` ou reativar `SPECIALIST_MODELS_ENABLED`.
- Upgrade de GPU (fora do controle de software).
