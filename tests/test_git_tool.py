import tools.git_tool as git_tool_mod
from tools.git_tool import GitTool


def _fake_result(stdout="ok", stderr=""):
    class FakeResult:
        pass
    r = FakeResult()
    r.stdout = stdout
    r.stderr = stderr
    return r


def test_combined_short_flag_bypass_now_blocked(tmp_path, monkeypatch):
    # achado real: "-f" in "-Df" é False (substring), então "git branch -Df x"
    # passava direto no check antigo.
    calls = []
    monkeypatch.setattr(git_tool_mod.subprocess, "run", lambda *a, **kw: calls.append(a) or _fake_result())

    result = GitTool().run({"repo": str(tmp_path), "command": "branch", "args": "-Df minha-branch"})

    assert "Bloqueado" in result
    assert calls == []


def test_long_force_flag_still_blocked(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(git_tool_mod.subprocess, "run", lambda *a, **kw: calls.append(a) or _fake_result())

    result = GitTool().run({"repo": str(tmp_path), "command": "fetch", "args": "--force"})

    assert "Bloqueado" in result
    assert calls == []


def test_quoted_multi_word_commit_message_preserved(tmp_path, monkeypatch):
    # achado real: args.split() ingênuo quebrava "-m \"duas palavras\"" em 3 tokens.
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return _fake_result()

    monkeypatch.setattr(git_tool_mod.subprocess, "run", fake_run)

    GitTool().run({"repo": str(tmp_path), "command": "commit", "args": '-m "duas palavras"'})

    assert captured["cmd"] == ["git", "commit", "-m", "duas palavras"]


def test_allowed_command_without_flags_runs(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(git_tool_mod.subprocess, "run", lambda *a, **kw: calls.append(a) or _fake_result("clean"))

    result = GitTool().run({"repo": str(tmp_path), "command": "status"})

    assert result == "clean"
    assert len(calls) == 1


def test_disallowed_subcommand_blocked(tmp_path):
    result = GitTool().run({"repo": str(tmp_path), "command": "push"})
    assert "Bloqueado" in result


def test_malformed_quotes_in_args_returns_error(tmp_path):
    result = GitTool().run({"repo": str(tmp_path), "command": "commit", "args": '-m "sem fechar'})
    assert "Erro" in result
