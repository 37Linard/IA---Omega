from tools.google_drive_tool import _escape_drive_query_value


def test_single_quote_escaped():
    assert _escape_drive_query_value("x' or fullText contains 'senha") == \
        "x\\' or fullText contains \\'senha"


def test_backslash_escaped_before_quote():
    assert _escape_drive_query_value("a\\b'c") == "a\\\\b\\'c"


def test_plain_text_unchanged():
    assert _escape_drive_query_value("relatorio mensal") == "relatorio mensal"


def test_escaped_value_cannot_break_out_of_query_clause():
    malicious = "x' or trashed=true or name contains 'y"
    escaped = _escape_drive_query_value(malicious)
    clause = f"name contains '{escaped}'"
    inner = clause[len("name contains '"):-1]
    # toda ' dentro do literal precisa estar escapada (\') — nenhuma sobra pra
    # fechar a string antes da hora e injetar cláusula extra
    i = 0
    while True:
        i = inner.find("'", i)
        if i == -1:
            break
        assert inner[i - 1] == "\\", f"' desprotegida na posição {i}: {inner!r}"
        i += 1
