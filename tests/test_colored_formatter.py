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
