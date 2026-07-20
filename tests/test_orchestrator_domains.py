from orchestrator import domain_hits, is_multi_domain, SPECIALISTS


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
