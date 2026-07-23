from tools.remember_fact_tool import RememberFactTool


class _FakeMemory:
    def __init__(self):
        self.saved = []

    def save_fact(self, fact):
        self.saved.append(fact)


def test_saves_fact_via_injected_memory():
    tool = RememberFactTool()
    fake = _FakeMemory()
    tool.memory = fake

    result = tool.run({"fact": "usuário prefere respostas curtas"})

    assert "usuário prefere respostas curtas" in result
    assert fake.saved == ["usuário prefere respostas curtas"]


def test_missing_fact_errors():
    tool = RememberFactTool()
    tool.memory = _FakeMemory()

    result = tool.run({})

    assert "obrigatório" in result


def test_lazily_creates_memory_when_not_injected(monkeypatch):
    import tools.remember_fact_tool as rf_mod
    fake = _FakeMemory()
    monkeypatch.setattr(rf_mod, "Memory", lambda: fake)

    tool = RememberFactTool()
    result = tool.run({"fact": "teste"})

    assert "teste" in result
    assert fake.saved == ["teste"]
