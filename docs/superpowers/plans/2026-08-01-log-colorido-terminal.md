# Log colorido no terminal do backend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Colorir o log do próprio agente (`log.info(...)` em `agent.py`/`orchestrator.py`/etc — uvicorn já colore sozinho) no terminal, destacando nível e prefixos de convenção já usados no código (`TAREFA:`, `EXECUTANDO:`, etc).

**Architecture:** Um `ColoredFormatter(logging.Formatter)` novo em `agent.py`, substitui a string de `format=` do `logging.basicConfig` já existente (linha 33) — único ponto de configuração, propaga por herança pra todo `logging.getLogger(__name__)` do resto do projeto. ANSI puro, sem lib nova.

**Tech Stack:** Python 3.14 (`C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe`), `logging` stdlib, pytest.

## Global Constraints

- Sem biblioteca nova (`colorlog`/`rich` fora de escopo — ver spec).
- Sem mudança na config do uvicorn.
- Sem redução de verbosidade/filtro de linhas.
- Formato NÃO colorido (quando `sys.stdout.isatty()` é `False`, ex: saída redirecionada) precisa continuar **byte-idêntico** ao formato atual (`"%(asctime)s [%(levelname)s] %(message)s"`) — nenhum teste/consumidor depende disso hoje (confirmado via `grep -rn "caplog\|basicConfig\|%(asctime)s\|%(levelname)s" tests/`, zero resultado), mas é a forma mais segura de garantir zero regressão em quem lê esse log (scripts, `eval_harness.py` output, etc.).
- Spec completa: `docs/superpowers/specs/2026-08-01-log-colorido-terminal-design.md`.

---

### Task 1: `ColoredFormatter`

**Files:**
- Modify: `agent.py:1-34` (import `re` já existe na linha 2; adiciona a classe `ColoredFormatter` antes do `logging.basicConfig`, troca `basicConfig` pra usar um `StreamHandler` com esse formatter)
- Test: `tests/test_colored_formatter.py` (novo)

**Interfaces:**
- Produces: `ColoredFormatter` (classe em `agent.py`, não exportada em `__all__` — importável direto via `from agent import ColoredFormatter`, mesmo padrão de outras classes do arquivo). Construtor aceita `use_color: bool | None = None` (`None` = autodetecta via `sys.stdout.isatty()`).

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/test_colored_formatter.py`:

```python
import logging

from agent import ColoredFormatter


def _record(level=logging.INFO, msg="mensagem qualquer"):
    return logging.LogRecord(
        name="test", level=level, pathname=__file__, lineno=1,
        msg=msg, args=(), exc_info=None,
    )


def test_sem_cor_reproduz_formato_antigo_byte_a_byte():
    fmt = ColoredFormatter(use_color=False)
    out = fmt.format(_record(msg="mensagem simples"))
    assert "\033[" not in out
    assert out.endswith("[INFO] mensagem simples")


def test_com_cor_nivel_info_nao_quebra_a_mensagem():
    fmt = ColoredFormatter(use_color=True)
    out = fmt.format(_record(msg="mensagem simples"))
    assert "mensagem simples" in out


def test_com_cor_prefixo_conhecido_fica_colorido():
    fmt = ColoredFormatter(use_color=True)
    out = fmt.format(_record(msg="TAREFA: calcule 2+2"))
    assert "\033[" in out
    assert "TAREFA" in out
    assert "calcule 2+2" in out


def test_com_cor_prefixo_step_sem_dois_pontos_fica_colorido():
    fmt = ColoredFormatter(use_color=True)
    out = fmt.format(_record(msg="STEP 1/8"))
    assert "\033[" in out
    assert "1/8" in out


def test_com_cor_mensagem_sem_prefixo_conhecido_nao_quebra():
    fmt = ColoredFormatter(use_color=True)
    out = fmt.format(_record(msg="mensagem sem prefixo nenhum"))
    assert "mensagem sem prefixo nenhum" in out


def test_com_cor_warning_usa_cor_de_nivel():
    fmt = ColoredFormatter(use_color=True)
    out = fmt.format(_record(level=logging.WARNING, msg="algo suspeito"))
    assert "\033[33m" in out  # amarelo
    assert "algo suspeito" in out


def test_com_cor_error_usa_cor_de_nivel():
    fmt = ColoredFormatter(use_color=True)
    out = fmt.format(_record(level=logging.ERROR, msg="quebrou"))
    assert "\033[1;31m" in out  # vermelho negrito
    assert "quebrou" in out
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest tests/test_colored_formatter.py -v --no-cov`
Expected: FAIL em todos — `ImportError: cannot import name 'ColoredFormatter' from 'agent'` (classe ainda não existe).

- [ ] **Step 3: Implementar `ColoredFormatter` em `agent.py`**

Em `agent.py`, trocar as linhas 33-34 (hoje):

```python
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)
```

Por:

```python
class ColoredFormatter(logging.Formatter):
    """Colore [LEVEL] e prefixos de convenção já usados no log do agente
    (TAREFA:, EXECUTANDO:, etc). Sem lib externa — só ANSI. use_color=None
    autodetecta via isatty() (sem cor se a saída for redirecionada/arquivo,
    pra não sujar log em disco com escape codes)."""

    _RESET = "\033[0m"
    _DIM   = "\033[2m"
    _LEVEL_COLORS = {
        "WARNING":  "\033[33m",
        "ERROR":    "\033[1;31m",
        "CRITICAL": "\033[1;31m",
        "DEBUG":    "\033[2m",
    }
    # Grupos por papel no fluxo ReAct — ciclo/ação/controle/conclusão
    _PREFIX_COLORS = {
        "TAREFA": "\033[34m", "STEP": "\033[34m",
        "EXECUTANDO": "\033[36m", "RESULTADO": "\033[36m",
        "ORCHESTRATOR": "\033[35m", "LOOP": "\033[35m", "PARSER": "\033[35m",
        "LLM": "\033[35m", "SPECIALIST MODEL": "\033[35m", "MODO CONVERSA": "\033[35m",
        "RESPOSTA FINAL": "\033[32m", "REFLECTION": "\033[32m",
    }
    _PREFIX_RE = re.compile(
        r"^(" + "|".join(re.escape(p) for p in sorted(_PREFIX_COLORS, key=len, reverse=True)) + r")\b:?"
    )

    def __init__(self, use_color: bool | None = None):
        super().__init__()
        self.use_color = sys.stdout.isatty() if use_color is None else use_color

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        ts = self.formatTime(record)
        if not self.use_color:
            return f"{ts} [{record.levelname}] {message}"

        level_color = self._LEVEL_COLORS.get(record.levelname, "")
        level_txt = f"{level_color}[{record.levelname}]{self._RESET}" if level_color else f"[{record.levelname}]"

        m = self._PREFIX_RE.match(message)
        if m:
            prefix = m.group(0)
            color = self._PREFIX_COLORS[m.group(1)]
            message = f"{color}{prefix}{self._RESET}{message[len(prefix):]}"

        return f"{self._DIM}{ts}{self._RESET} {level_txt} {message}"


_handler = logging.StreamHandler()
_handler.setFormatter(ColoredFormatter())
logging.basicConfig(level=logging.INFO, handlers=[_handler])
log = logging.getLogger(__name__)
```

`re` e `sys` já estão importados no topo do arquivo (linhas 2 e 6) — nenhum
import novo necessário.

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest tests/test_colored_formatter.py -v --no-cov`
Expected: PASS — todos os 7 testes.

- [ ] **Step 5: Rodar a suite completa (regressão)**

Run: `C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe -m pytest`
Expected: todos passam (baseline 387 antes desta task, agora +7 — nenhuma
regressão nos demais; nenhum teste existente depende do formato exato do
log, confirmado antes de escrever este plano).

- [ ] **Step 6: Commit**

```bash
git add agent.py tests/test_colored_formatter.py
git commit -m "feat: log colorido no terminal (nivel + prefixos de convencao)"
```

---

### Task 2: Validação visual real

**Files:** nenhum (validação).

- [ ] **Step 1: Terminal real (com cor)**

Checar se já tem processo na 8000 travado (`netstat -ano | grep :8000`,
`taskkill` se achar); rodar `iniciar_frontend.bat` numa janela de terminal
de verdade (não redirecionado — duplo clique no `.bat`, não via pipe).
Disparar uma tarefa real pelo frontend (`http://localhost:8000`) e conferir
visualmente no terminal: `[INFO]` sem cor especial, prefixos `TAREFA:`/
`STEP`/`EXECUTANDO:`/`RESULTADO:`/`RESPOSTA FINAL:` coloridos e
diferenciados por grupo, texto continua legível (sem código de escape
"vazando" como texto literal).

- [ ] **Step 2: Saída redirecionada (sem cor, regressão)**

Run: `C:\Users\User\AppData\Local\Python\pythoncore-3.14-64\python.exe -m uvicorn api:app --port 8001 > scratch_log_test.txt 2>&1` por ~5s
(`timeout 5` ou equivalente, depois `taskkill` no PID da 8001), então:

```bash
grep -c $'\033' scratch_log_test.txt   # deve ser 0
```

Expected: 0 ocorrências de ESC — confirma que saída redirecionada continua
sem ANSI (autodetectado via `isatty()`). Apagar `scratch_log_test.txt`
depois (arquivo de teste, não faz parte do repo).

- [ ] **Step 3: Reportar resultado**

Sem commit nesse passo (validação pura).
