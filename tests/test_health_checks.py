from health_checks import jwt_secret_warning, remote_access_warning


def test_warns_when_auth_enabled_but_jwt_secret_empty():
    result = jwt_secret_warning("minha-senha", "")
    assert "forjáveis" in result
    assert result != ""


def test_no_warning_when_auth_disabled_regardless_of_jwt_secret():
    assert jwt_secret_warning("", "") == ""
    assert jwt_secret_warning("", "algum-segredo") == ""


def test_no_warning_when_both_configured():
    assert jwt_secret_warning("minha-senha", "segredo-forte") == ""


def test_remote_access_warns_when_auth_password_empty():
    result = remote_access_warning("")
    assert "AUTH_PASSWORD" in result
    assert result != ""


def test_remote_access_no_warning_when_auth_password_set():
    assert remote_access_warning("minha-senha") == ""
