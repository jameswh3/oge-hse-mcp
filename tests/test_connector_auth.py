from dataclasses import dataclass

from oge_hse_mcp import auth, connector_server


@dataclass(frozen=True)
class _Token:
    claims: dict[str, object]


def test_verifier_accepts_primary_and_teams_sso_audiences(monkeypatch):
    captured: dict[str, object] = {}

    class _SigningKey:
        key = object()

    class _Jwks:
        def get_signing_key_from_jwt(self, _token):
            return _SigningKey()

    def decode(_token, _key, *, algorithms, audience, issuer):
        captured.update(algorithms=algorithms, audience=audience, issuer=issuer)
        return {"aud": "teams-audience"}

    monkeypatch.setattr(auth, "_openid_configuration", lambda _tenant_id: {"jwks_uri": "https://example.test/jwks"})
    verifier = auth.EntraTokenVerifier(
        auth.EntraTokenConfig("tenant", ("primary-audience", "teams-audience"), "issuer")
    )
    verifier._jwks = _Jwks()
    monkeypatch.setattr(auth.jwt, "decode", decode)

    assert verifier._validate("token") == {"aud": "teams-audience"}
    assert captured == {
        "algorithms": ["RS256"],
        "audience": ("primary-audience", "teams-audience"),
        "issuer": "issuer",
    }


def test_claim_sites_are_used_when_request_omits_sites(monkeypatch):
    monkeypatch.setenv("HSE_REQUIRE_AUTH", "true")
    monkeypatch.setattr(connector_server, "get_access_token", lambda: _Token({"site_ids": ["DEMO-GULF"]}))

    assert connector_server._authorized_sites() == ["DEMO-GULF"]


def test_requested_site_must_be_in_delegated_claim(monkeypatch):
    monkeypatch.setenv("HSE_REQUIRE_AUTH", "true")
    monkeypatch.setattr(connector_server, "get_access_token", lambda: _Token({"site_ids": ["DEMO-GULF"]}))

    try:
        connector_server._authorized_sites(["DEMO-PERMIAN"])
        assert False, "Expected unauthorized site to be rejected"
    except ValueError as exc:
        assert "not authorized" in str(exc)


def test_empty_site_claim_does_not_grant_requested_site(monkeypatch):
    monkeypatch.setenv("HSE_REQUIRE_AUTH", "true")
    monkeypatch.setattr(connector_server, "get_access_token", lambda: _Token({}))

    try:
        connector_server._authorized_sites(["DEMO-GULF"])
        assert False, "Expected missing site authorization to be rejected"
    except ValueError as exc:
        assert "not authorized" in str(exc)
