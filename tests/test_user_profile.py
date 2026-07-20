import pytest

import user_profile as up
from user_profile import UserProfile, _detect_tech_signal, _level_from_score


@pytest.fixture
def isolated_profile(tmp_path, monkeypatch):
    """UserProfile isolado — nunca toca workspace/user_profile.json real."""
    monkeypatch.setattr(up, "PROFILE_FILE", str(tmp_path / "user_profile.json"))
    return UserProfile()


def test_advanced_jargon_gives_positive_signal():
    signal = _detect_tech_signal("preciso refatorar o middleware pra usar async/await e cache")
    assert signal > 0


def test_beginner_phrase_gives_negative_signal():
    signal = _detect_tech_signal("sou iniciante, não entendi nada disso, explica simples")
    assert signal < 0


def test_neutral_text_gives_no_signal():
    assert _detect_tech_signal("bom dia, tudo bem?") == 0.0


def test_level_from_score_thresholds():
    assert _level_from_score(1.5) == "especialista"
    assert _level_from_score(0.5) == "avançado"
    assert _level_from_score(0.0) == "intermediário"
    assert _level_from_score(-1.0) == "iniciante"


def test_observe_message_waits_for_minimum_observations(isolated_profile):
    profile = isolated_profile
    profile.observe_message("refatorar middleware com async await e cache distribuído")
    assert profile.data["tech_level"] == "intermediário"  # ainda não ajustou (< 3 observações)
    assert profile.data["tech_observations"] == 1


def test_observe_message_adjusts_level_after_enough_signal(isolated_profile):
    profile = isolated_profile
    msg = "refatorar arquitetura de microserviço com kubernetes, docker, async/await e mutex"
    for _ in range(5):
        profile.observe_message(msg)
    assert profile.data["tech_level"] in ("avançado", "especialista")


def test_observe_message_respects_manual_lock(isolated_profile):
    profile = isolated_profile
    profile.update(tech_level="iniciante", tech_level_auto=False)
    msg = "refatorar arquitetura de microserviço com kubernetes, docker, async/await e mutex"
    for _ in range(5):
        profile.observe_message(msg)
    assert profile.data["tech_level"] == "iniciante"  # travado manualmente, não muda


def test_observe_message_extracts_interests(isolated_profile):
    profile = isolated_profile
    profile.observe_message("estou aprendendo rust e sistemas operacionais")
    assert any("rust" in t for t in profile.data["topics_interest"])


def test_profile_persists_across_instances(tmp_path, monkeypatch):
    monkeypatch.setattr(up, "PROFILE_FILE", str(tmp_path / "user_profile.json"))
    p1 = UserProfile()
    p1.update(name="Gabriel")
    p2 = UserProfile()
    assert p2.data["name"] == "Gabriel"
