import tools.generate_report_tool as gr_mod
from tools.generate_report_tool import GenerateReportTool


def test_generates_report_with_all_sections(tmp_path, monkeypatch):
    monkeypatch.setattr(gr_mod, "_WORKSPACE", str(tmp_path))

    result = GenerateReportTool().run({
        "title": "Relatório de Teste",
        "summary": "resumo aqui",
        "data": "dados aqui",
        "analysis": "análise aqui",
        "alerts": "alerta aqui",
        "sources": "fonte aqui",
        "filename": "teste.md",
    })

    assert "salvo" in result.lower()
    content = (tmp_path / "teste.md").read_text(encoding="utf-8")
    assert "# Relatório de Teste" in content
    assert "## Resumo Executivo" in content
    assert "resumo aqui" in content
    assert "## Dados" in content
    assert "## Análise Técnica" in content
    assert "## ⚠️ Alertas e Riscos" in content
    assert "## Fontes" in content


def test_optional_sections_omitted_when_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(gr_mod, "_WORKSPACE", str(tmp_path))

    GenerateReportTool().run({"title": "Só resumo", "summary": "x", "filename": "r.md"})

    content = (tmp_path / "r.md").read_text(encoding="utf-8")
    assert "## Dados" not in content
    assert "## Fontes" not in content


def test_filename_sanitized_via_basename(tmp_path, monkeypatch):
    monkeypatch.setattr(gr_mod, "_WORKSPACE", str(tmp_path))

    GenerateReportTool().run({"title": "x", "filename": "../../evil.md"})

    assert (tmp_path / "evil.md").exists()


def test_filename_without_md_extension_gets_one(tmp_path, monkeypatch):
    monkeypatch.setattr(gr_mod, "_WORKSPACE", str(tmp_path))

    GenerateReportTool().run({"title": "x", "filename": "semextensao"})

    assert (tmp_path / "semextensao.md").exists()


def test_default_filename_has_timestamp(tmp_path, monkeypatch):
    monkeypatch.setattr(gr_mod, "_WORKSPACE", str(tmp_path))

    GenerateReportTool().run({"title": "sem nome"})

    files = list(tmp_path.glob("relatorio_*.md"))
    assert len(files) == 1
