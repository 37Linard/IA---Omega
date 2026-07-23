from tools.browser_tool import _is_blocked_url


def test_localhost_blocked():
    assert _is_blocked_url("http://localhost:11434/api/generate") is True


def test_localhost_subdomain_blocked():
    assert _is_blocked_url("http://foo.localhost/") is True


def test_loopback_ip_blocked():
    assert _is_blocked_url("http://127.0.0.1:8000/") is True


def test_private_lan_ip_blocked():
    assert _is_blocked_url("http://192.168.1.1/admin") is True


def test_link_local_metadata_ip_blocked():
    assert _is_blocked_url("http://169.254.169.254/latest/meta-data/") is True


def test_mdns_local_blocked():
    assert _is_blocked_url("http://minha-impressora.local/") is True


def test_normal_public_url_allowed():
    assert _is_blocked_url("https://example.com/pagina") is False


def test_public_ip_allowed():
    assert _is_blocked_url("http://93.184.216.34/") is False


def test_malformed_url_blocked():
    assert _is_blocked_url("http://") is True
