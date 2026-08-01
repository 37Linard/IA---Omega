# Log colorido no terminal do backend

## Contexto

Usuário roda o backend via `iniciar_frontend.bat` (uvicorn + logs do agente
no mesmo console). Uvicorn já coloriza sozinho quando a saída é um terminal
real (perde cor só quando redirecionada — confirmado nos testes desta sessão
rodando em background com output pra arquivo). O que falta cor é o logger
próprio do projeto: `logging.basicConfig(level=logging.INFO,
format="%(asctime)s [%(levelname)s] %(message)s")` em `agent.py:33` — único
ponto de configuração, todo o resto do código (`orchestrator.py`, `llm.py`,
`scheduler.py`, etc.) usa `logging.getLogger(__name__)`, que herda esse
formato.

Convenção já existente no código (não inventada agora): várias linhas de log
usam um prefixo maiúsculo antes dos dois-pontos pra marcar o tipo de evento
— `grep` confirmou os seguintes prefixos em uso real: `TAREFA:`, `STEP`
(sem dois-pontos, formato `"STEP %d/%d"`), `EXECUTANDO:`, `RESULTADO:`,
`RESPOSTA FINAL:`, `REFLECTION:`, `ORCHESTRATOR:`, `PARSER:`, `LOOP:`,
`LLM:`, `MODO CONVERSA:`, `SPECIALIST MODEL:`.

## Decisão

Novo `ColoredFormatter(logging.Formatter)` em `agent.py`, substitui o
`format=` string do `basicConfig` atual — sem biblioteca nova, só códigos
ANSI (`\033[...m`).

- **Timestamp**: cinza (dim).
- **`[LEVELNAME]`**: colorido por nível — `INFO` sem cor especial (branco/
  padrão do terminal), `WARNING` amarelo, `ERROR`/`CRITICAL` vermelho
  negrito, `DEBUG` cinza escuro.
- **Prefixos de convenção** (lista acima): cada um ganha uma cor fixa
  aplicada só ao prefixo (não a mensagem inteira) — agrupados por papel no
  fluxo ReAct: ciclo (`TAREFA`, `STEP`) em azul, ação (`EXECUTANDO`,
  `RESULTADO`) em ciano, controle (`ORCHESTRATOR`, `LOOP`, `PARSER`,
  `LLM`, `SPECIALIST MODEL`, `MODO CONVERSA`) em magenta, conclusão
  (`RESPOSTA FINAL`, `REFLECTION`) em verde. Cor exata de cada grupo é
  detalhe de implementação, não trava aqui.
- **Detecção de TTY**: `sys.stdout.isatty()` checado 1x na criação do
  formatter — se `False` (saída redirecionada pra arquivo/pipe, como nos
  testes desta sessão), usa o formato antigo sem ANSI. Evita sujar log em
  disco com códigos de escape.

## Fora de escopo

Mexer na configuração/formato do uvicorn (já colore sozinho em terminal
real). Reduzir verbosidade ou filtrar linhas (usuário confirmou que o
problema é falta de cor, não volume). Adicionar biblioteca externa
(`colorlog`/`rich`) — ANSI direto é suficiente pro escopo e mantém a
filosofia de dependência mínima já seguida no projeto (`tools/_security.py`,
`tools/_schema.py` etc. também não usam libs externas pra isso que fazem).

## Testagem

Sem suite automatizada — saída de log formatada não tem valor de asserção
automática direto (é sobre legibilidade visual). Validação real: rodar o
backend num terminal de verdade (não redirecionado) e conferir visualmente
que os prefixos aparecem coloridos e o resto do texto continua legível;
rodar com saída redirecionada pra arquivo (`> log.txt`) e conferir que o
arquivo não tem códigos ANSI (regressão do path não-TTY). `pytest` da suite
existente continua verde — nenhum teste depende do formato exato da string
de log (confirmado por `grep -rn "caplog\|format=" tests/` antes de
implementar, checar de novo no plano se algo aparecer).
