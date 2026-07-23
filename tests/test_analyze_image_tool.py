import tools.analyze_image_tool as ai_mod
from tools.analyze_image_tool import AnalyzeImageTool


def test_missing_path_errors():
    result = AnalyzeImageTool().run({})
    assert "obrigatório" not in result and "forneça" in result.lower()


def test_blocks_path_outside_allowed_dirs(tmp_path, monkeypatch):
    allowed = tmp_path / "Desktop"
    outside = tmp_path / "Desktop-secret"
    allowed.mkdir()
    outside.mkdir()
    monkeypatch.setattr(ai_mod, "ALLOWED_READ_DIRS", [str(allowed)])
    f = outside / "foto.png"
    f.write_bytes(b"fake-png-bytes")

    result = AnalyzeImageTool().run({"path": str(f)})

    assert "não permitido" in result


def test_nonexistent_file_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_mod, "ALLOWED_READ_DIRS", [str(tmp_path)])

    result = AnalyzeImageTool().run({"path": str(tmp_path / "nao_existe.png")})

    assert "não encontrado" in result


def test_unsupported_extension_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_mod, "ALLOWED_READ_DIRS", [str(tmp_path)])
    f = tmp_path / "arquivo.txt"
    f.write_text("x", encoding="utf-8")

    result = AnalyzeImageTool().run({"path": str(f)})

    assert "não suportado" in result


def test_valid_image_calls_vision_model(tmp_path, monkeypatch):
    monkeypatch.setattr(ai_mod, "ALLOWED_READ_DIRS", [str(tmp_path)])
    f = tmp_path / "foto.png"
    f.write_bytes(b"fake-png-bytes")

    import llm as llm_mod
    calls = {}

    class FakeLLM:
        def generate_vision(self, prompt, image_b64, model=""):
            calls["prompt"] = prompt
            calls["model"] = model
            return "uma foto de teste"

    monkeypatch.setattr(llm_mod, "OllamaLLM", FakeLLM)

    result = AnalyzeImageTool().run({"path": str(f), "prompt": "o que é isso?"})

    assert "uma foto de teste" in result
    assert calls["prompt"] == "o que é isso?"
