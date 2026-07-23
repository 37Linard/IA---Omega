import tools.generate_chart_tool as gc_mod
from tools.generate_chart_tool import GenerateChartTool


def test_bar_chart_saves_file(tmp_path, monkeypatch):
    monkeypatch.setattr(gc_mod, "CHART_DIR", str(tmp_path))

    result = GenerateChartTool().run({
        "type": "bar", "labels": ["Jan", "Fev"], "values": [10, 20], "output": "g.png",
    })

    assert "salvo" in result.lower()
    assert (tmp_path / "g.png").exists()


def test_invalid_type_errors():
    result = GenerateChartTool().run({"type": "hexagono", "values": [1]})
    assert "inválido" in result.lower()


def test_missing_values_errors():
    result = GenerateChartTool().run({"type": "bar", "values": []})
    assert "obrigatório" in result


def test_pie_chart_without_labels(tmp_path, monkeypatch):
    monkeypatch.setattr(gc_mod, "CHART_DIR", str(tmp_path))

    result = GenerateChartTool().run({"type": "pie", "values": [1, 2, 3], "output": "p.png"})

    assert (tmp_path / "p.png").exists()


def test_output_filename_sanitized_via_basename(tmp_path, monkeypatch):
    monkeypatch.setattr(gc_mod, "CHART_DIR", str(tmp_path))

    GenerateChartTool().run({"type": "bar", "values": [1, 2], "output": "../../evil.png"})

    assert (tmp_path / "evil.png").exists()


def test_output_without_png_extension_gets_one(tmp_path, monkeypatch):
    monkeypatch.setattr(gc_mod, "CHART_DIR", str(tmp_path))

    GenerateChartTool().run({"type": "bar", "values": [1, 2], "output": "semextensao"})

    assert (tmp_path / "semextensao.png").exists()


def test_mismatched_labels_length_falls_back_to_indices(tmp_path, monkeypatch):
    monkeypatch.setattr(gc_mod, "CHART_DIR", str(tmp_path))

    result = GenerateChartTool().run({
        "type": "bar", "labels": ["so-um"], "values": [1, 2, 3], "output": "x.png",
    })

    assert "salvo" in result.lower()
