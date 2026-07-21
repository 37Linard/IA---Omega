import threading

import agent as agent_mod
import orchestrator
import plan_store
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
    def __init__(self, responses):
        self.model = "test-model"
        self.responses = list(responses)
        self.calls = []

    def generate(self, prompt, on_token=None):
        self.calls.append(prompt)
        resp = self.responses.pop(0)
        if on_token:
            for ch in resp:
                on_token(ch)
        return resp


def _bare_agent(llm, session_id=""):
    a = ReActAgent.__new__(ReActAgent)
    a.llm                = llm
    a.tools               = {}
    a.memory              = _StubMemory()
    a.profile             = _StubProfile()
    a._cancel             = threading.Event()
    a._cancel_reason      = "usuário"
    a.conversation        = []
    a.specialist_context  = ""
    a.session_id          = session_id
    a._emit               = None
    return a


TASK = "pesquisa o preço do bitcoin e salva num arquivo bitcoin.txt"


def test_compound_task_finishes_and_clears_persisted_plan(monkeypatch):
    monkeypatch.setattr(orchestrator, "is_multi_domain", lambda *a, **k: True)
    llm = _ScriptedLLM([
        "1. Usar web_search para pesquisar o preço do bitcoin\n2. Usar write_file para salvar em bitcoin.txt",
        "Thought: pronto.\nFinal Answer: preço pesquisado com sucesso",
        "Thought: pronto.\nFinal Answer: arquivo salvo com sucesso",
    ])
    a = _bare_agent(llm)

    result = a.run(TASK, step_callback=None)

    assert "Tarefa concluída em 2 passos" in result
    assert plan_store.find_incomplete() is None  # terminou -> não sobra nada pra retomar


def test_crash_mid_plan_resumes_from_correct_step(monkeypatch):
    monkeypatch.setattr(orchestrator, "is_multi_domain", lambda *a, **k: True)

    # Simula um plano deixado 'running' por um crash: passo 1 já concluído,
    # passo 2 nunca rodou (arquivo nunca foi apagado porque o processo morreu).
    pid = plan_store.new_id()
    steps = ["Usar web_search para pesquisar o preço do bitcoin", "Usar write_file para salvar em bitcoin.txt"]
    plan_store.save(pid, TASK, steps, {"tarefa_original": TASK}, current_index=0)
    plan_store.update_progress(pid, 1, {"tarefa_original": TASK, "passo_1": "preço pesquisado com sucesso"})

    llm = _ScriptedLLM(["Thought: pronto.\nFinal Answer: arquivo salvo com sucesso"])
    a = _bare_agent(llm)

    result = a.run(TASK, step_callback=None)

    assert len(llm.calls) == 1  # não replanejou nem re-executou o passo 1 — só rodou o passo 2
    assert "preço pesquisado com sucesso" in result  # resultado do passo 1 (do crash) preservado
    assert "arquivo salvo com sucesso" in result
    assert plan_store.find_incomplete() is None


def test_resume_keyword_triggers_resume_with_different_task_text(monkeypatch):
    monkeypatch.setattr(orchestrator, "is_multi_domain", lambda *a, **k: True)

    pid = plan_store.new_id()
    steps = ["passo A", "passo B"]
    plan_store.save(pid, TASK, steps, {"tarefa_original": TASK}, current_index=1)
    plan_store.update_progress(pid, 1, {"tarefa_original": TASK, "passo_1": "resultado A"})

    llm = _ScriptedLLM(["Thought: pronto.\nFinal Answer: resultado B"])
    a = _bare_agent(llm)

    result = a.run("continua de onde parou por favor", step_callback=None)

    assert len(llm.calls) == 1
    assert "resultado B" in result
    assert plan_store.find_incomplete() is None


def test_unrelated_compound_task_does_not_resume_stale_plan(monkeypatch):
    monkeypatch.setattr(orchestrator, "is_multi_domain", lambda *a, **k: True)

    pid = plan_store.new_id()
    plan_store.save(pid, TASK, ["passo A", "passo B"], {"tarefa_original": TASK}, current_index=1)
    plan_store.update_progress(pid, 1, {"tarefa_original": TASK, "passo_1": "resultado A"})

    other_task = "gera um relatório de vendas e envia por email pro time"
    llm = _ScriptedLLM([
        "1. Usar generate_report para gerar o relatório\n2. Usar email para enviar",
        "Thought: pronto.\nFinal Answer: relatório gerado",
        "Thought: pronto.\nFinal Answer: email enviado",
    ])
    a = _bare_agent(llm)

    a.run(other_task, step_callback=None)

    # o plano velho (tarefa diferente, sem palavra de retomada) continua intacto
    stale = plan_store.find_incomplete()
    assert stale is not None
    assert stale["id"] == pid
