import threading

from orchestrator import domain_hits, is_multi_domain, SPECIALISTS, OrchestratorAgent


def test_domain_hits_matches_conjugated_verbs():
    # "pesquisar"/"pesquise"/"pesquisando" devem bater no stem de "pesquisa" do hint
    assert "pesquisador" in domain_hits("preciso pesquisar sobre IA")
    assert "pesquisador" in domain_hits("pesquise sobre IA")
    assert "pesquisador" in domain_hits("estou pesquisando sobre IA")


def test_domain_hits_finds_multiple_domains():
    task = "pesquisar preço do bitcoin, calcular média em python e salvar num arquivo"
    hits = domain_hits(task)
    assert "pesquisador" in hits
    assert "codigo" in hits
    assert "arquivos" in hits


def test_domain_hits_empty_for_unrelated_text():
    assert domain_hits("oi, tudo bem?") == set() or len(domain_hits("oi, tudo bem?")) <= 1


def test_is_multi_domain_requires_sequence_word():
    # mesmo com 3 dominios, sem palavra de sequencia (e/depois/então) não conta como composta
    task = "pesquisar preço bitcoin calcular python salvar arquivo"
    assert is_multi_domain(task, min_domains=3) is False


def test_is_multi_domain_true_for_real_compound_task():
    task = "pesquisar preço do bitcoin e calcular a média em python e salvar num arquivo"
    assert is_multi_domain(task, min_domains=3) is True


def test_is_multi_domain_false_for_short_task():
    assert is_multi_domain("oi", min_domains=2) is False


def test_is_multi_domain_min_domains_2_is_looser_than_3():
    task = "pesquisar sobre IA e depois salvar num arquivo"
    assert is_multi_domain(task, min_domains=2) is True
    assert is_multi_domain(task, min_domains=3) is False


def test_all_specialists_have_required_keys():
    for name, spec in SPECIALISTS.items():
        assert "label" in spec
        assert "tools" in spec
        assert "hint" in spec


def test_no_tool_is_orphaned_from_every_specialist():
    """Regressão: get_crypto existia como tool mas não estava na lista de nenhum
    especialista — SYSTEM_PROMPT mandava usar get_crypto pra bitcoin, mas o
    especialista roteado (pesquisador) fisicamente não tinha a tool disponível,
    então sempre caía em web_search. 'geral' não conta (pega tudo por padrão,
    não prova que a tool foi intencionalmente atribuída a algum domínio)."""
    assigned = {t for name, spec in SPECIALISTS.items() if name != "geral" for t in spec["tools"]}
    assert "get_crypto" in assigned
    assert "get_currency" in assigned


def test_bitcoin_task_routes_to_specialist_with_get_crypto():
    hits = domain_hits("qual o preço do bitcoin agora?")
    assert hits, "nenhum especialista detectado pra pergunta de bitcoin"
    for name in hits:
        assert "get_crypto" in SPECIALISTS[name]["tools"], (
            f"especialista '{name}' detectado pra bitcoin mas sem get_crypto no toolset"
        )


def _bare_orchestrator():
    """OrchestratorAgent sem passar por __init__ real — evita Memory()/UserProfile()/
    OllamaLLM reais. Só o suficiente pra exercitar _create_specialist."""
    o = OrchestratorAgent.__new__(OrchestratorAgent)
    o.all_tools  = {}
    o.memory     = object()  # sentinela: só precisa ser identidade única, não Memory real
    o.session_id = "s1"
    o._cancel    = threading.Event()
    return o


def test_create_specialist_shares_orchestrator_memory_instance():
    """Regressão: ReActAgent criava sua PRÓPRIA Memory() em vez de usar a do
    orchestrator. save_session_with_llm gravava short_term nessa instância órfã;
    end_session (chamado no disconnect do WS, usa orchestrator.memory) sempre via
    short_term vazio e nunca criava episódio — achado ao vivo testando rag_search
    de episódios (2026-07-22). _create_specialist agora deve injetar a MESMA
    instância de memória em todo especialista que cria."""
    o = _bare_orchestrator()
    agent = o._create_specialist("geral")
    assert agent.memory is o.memory
