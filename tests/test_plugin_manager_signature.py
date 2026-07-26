"""Verificação de assinatura Ed25519 no plugin_manager — hash sozinho só prova
que "o código bate com o manifest", não prova QUEM escreveu o manifest
(atacante controla os dois lados). Assinatura verifica contra uma chave
pública que o OPERADOR confiou manualmente antes (trust_author), nunca
baixada automaticamente."""
import hashlib
import json

import requests

import plugin_manager as pm


class _FakeResponse:
    def __init__(self, json_data=None, text=""):
        self._json = json_data
        self.text = text

    def raise_for_status(self):
        pass

    def json(self):
        return self._json


CODE = "def run(params):\n    return 'oi'\n"
CODE_HASH = hashlib.sha256(CODE.encode("utf-8")).hexdigest()


def _manifest(name="meu_plugin", version="1.0.0", author_id="autor1",
              signature=None, code_sha256=CODE_HASH):
    return {
        "name": name, "version": version, "description": "teste",
        "code_url": "https://example.com/meu_plugin.py",
        "code_sha256": code_sha256, "author_id": author_id,
        "signature": signature or "00" * 64,
    }


def _mock_fetch(monkeypatch, manifest, code=CODE):
    def fake_get(url, timeout=None):
        if "manifest" in url or url == "https://example.com/manifest.json":
            return _FakeResponse(json_data=manifest)
        return _FakeResponse(text=code)
    monkeypatch.setattr(requests, "get", fake_get)


def _isolate_plugins_dir(monkeypatch, tmp_path):
    plugins_dir = tmp_path / "plugins"
    monkeypatch.setattr(pm, "PLUGINS_DIR", str(plugins_dir))
    monkeypatch.setattr(pm, "TRUSTED_AUTHORS_FILE", str(plugins_dir / "trusted_authors.json"))


def test_generate_keypair_sign_and_verify_roundtrip(monkeypatch, tmp_path):
    _isolate_plugins_dir(monkeypatch, tmp_path)
    priv_hex, pub_hex = pm.generate_keypair()
    pm.trust_author("autor1", pub_hex)

    sig = pm.sign_payload("meu_plugin", "1.0.0", CODE_HASH, priv_hex)
    manifest = _manifest(signature=sig)

    pm._verify_signature(manifest, CODE_HASH)  # não levanta


def test_trust_author_rejects_invalid_pubkey(monkeypatch, tmp_path):
    _isolate_plugins_dir(monkeypatch, tmp_path)

    try:
        pm.trust_author("autor1", "isso-nao-e-hex-valido")
        assert False, "deveria ter rejeitado"
    except pm.PluginError:
        pass

    assert pm.list_trusted_authors() == []  # nao gravou nada


def test_stage_rejects_unknown_author(monkeypatch, tmp_path):
    _isolate_plugins_dir(monkeypatch, tmp_path)
    _mock_fetch(monkeypatch, _manifest())  # autor1 nunca foi confiado

    try:
        pm.stage("https://example.com/manifest.json")
        assert False, "deveria ter rejeitado autor desconhecido"
    except pm.PluginError as e:
        assert "NÃO CONFIADO" in str(e)

    assert pm.list_staged() == []  # nada foi escrito em disco


def test_stage_rejects_tampered_signature(monkeypatch, tmp_path):
    _isolate_plugins_dir(monkeypatch, tmp_path)
    priv_hex, pub_hex = pm.generate_keypair()
    pm.trust_author("autor1", pub_hex)

    # assina o hash ERRADO -- simula manifest onde a assinatura nao bate
    # com o codigo real (adulterado depois de assinado, ou forjado)
    wrong_hash = "0" * 64
    sig = pm.sign_payload("meu_plugin", "1.0.0", wrong_hash, priv_hex)
    _mock_fetch(monkeypatch, _manifest(signature=sig))

    try:
        pm.stage("https://example.com/manifest.json")
        assert False, "deveria ter rejeitado assinatura invalida"
    except pm.PluginError as e:
        assert "ASSINATURA INVÁLIDA" in str(e)

    assert pm.list_staged() == []


def test_stage_rejects_signature_replayed_from_different_version(monkeypatch, tmp_path):
    """Prova que o payload assinado inclui name+version, nao só o hash --
    senão uma assinatura válida da v1.0.0 poderia ser reaproveitada pra
    'autenticar' uma v2.0.0 maliciosa com o mesmo hash por coincidência,
    ou pra outro plugin cujo código gera o mesmo hash."""
    _isolate_plugins_dir(monkeypatch, tmp_path)
    priv_hex, pub_hex = pm.generate_keypair()
    pm.trust_author("autor1", pub_hex)

    sig_for_v1 = pm.sign_payload("meu_plugin", "1.0.0", CODE_HASH, priv_hex)
    manifest_v2 = _manifest(version="2.0.0", signature=sig_for_v1)
    _mock_fetch(monkeypatch, manifest_v2)

    try:
        pm.stage("https://example.com/manifest.json")
        assert False, "assinatura da v1.0.0 nao deveria validar pra v2.0.0"
    except pm.PluginError as e:
        assert "ASSINATURA INVÁLIDA" in str(e)


def test_stage_succeeds_with_trusted_author_and_valid_signature(monkeypatch, tmp_path):
    _isolate_plugins_dir(monkeypatch, tmp_path)
    priv_hex, pub_hex = pm.generate_keypair()
    pm.trust_author("autor1", pub_hex)
    sig = pm.sign_payload("meu_plugin", "1.0.0", CODE_HASH, priv_hex)
    _mock_fetch(monkeypatch, _manifest(signature=sig))

    name = pm.stage("https://example.com/manifest.json")

    assert name == "meu_plugin"
    staged = pm.list_staged()
    assert staged == [{"name": "meu_plugin", "status": "staged"}]


def test_fetch_manifest_requires_author_and_signature_fields():
    incomplete = {"name": "x", "version": "1.0.0", "description": "d",
                  "code_url": "https://x", "code_sha256": "abc"}
    # sem author_id/signature -- schema antigo, deve ser rejeitado agora
    missing = pm.REQUIRED_MANIFEST_FIELDS - incomplete.keys()
    assert missing == {"author_id", "signature"}


def test_untrust_author_removes_from_store(monkeypatch, tmp_path):
    _isolate_plugins_dir(monkeypatch, tmp_path)
    _, pub_hex = pm.generate_keypair()
    pm.trust_author("autor1", pub_hex)
    assert len(pm.list_trusted_authors()) == 1

    pm.untrust_author("autor1")

    assert pm.list_trusted_authors() == []
