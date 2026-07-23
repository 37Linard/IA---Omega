import os
from tools._paths import is_allowed_path


def test_path_inside_allowed_dir_permitted(tmp_path):
    allowed = str(tmp_path / "Desktop")
    os.makedirs(allowed)
    target = os.path.join(allowed, "arquivo.txt")

    assert is_allowed_path(target, [allowed]) is True


def test_sibling_dir_with_matching_prefix_blocked(tmp_path):
    # achado real 2026-07-23: "Desktop-secret" passava como se fosse dentro de
    # "Desktop" porque startswith() bate por prefixo de string, sem checar
    # separador de path.
    desktop = str(tmp_path / "Desktop")
    secret = str(tmp_path / "Desktop-secret")
    os.makedirs(desktop)
    os.makedirs(secret)
    target = os.path.join(secret, "arquivo.txt")

    assert is_allowed_path(target, [desktop]) is False


def test_allowed_dir_itself_permitted(tmp_path):
    allowed = str(tmp_path / "Desktop")
    os.makedirs(allowed)

    assert is_allowed_path(allowed, [allowed]) is True


def test_unrelated_dir_blocked(tmp_path):
    allowed = str(tmp_path / "Desktop")
    other = str(tmp_path / "Other")
    os.makedirs(allowed)
    os.makedirs(other)

    assert is_allowed_path(os.path.join(other, "x.txt"), [allowed]) is False


def test_matches_any_of_multiple_allowed_dirs(tmp_path):
    d1 = str(tmp_path / "Desktop")
    d2 = str(tmp_path / "Documents")
    os.makedirs(d1)
    os.makedirs(d2)
    target = os.path.join(d2, "nota.txt")

    assert is_allowed_path(target, [d1, d2]) is True
