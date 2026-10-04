import base64

import pytest

from app.auth.api_key import Credentials, normalize_domain
from app.freshdesk.errors import AuthenticationError, ConfigurationError
from tests.helpers import build_service, json_response


def test_from_env_reads_credentials():
    creds = Credentials.from_env({"FRESHDESK_DOMAIN": "acme", "FRESHDESK_API_KEY": "secret"})
    assert creds.base_url == "https://acme.freshdesk.com/api/v2"


@pytest.mark.parametrize("env", [{}, {"FRESHDESK_DOMAIN": "acme"}, {"FRESHDESK_API_KEY": "k"}])
def test_missing_values_rejected(env):
    with pytest.raises(ConfigurationError):
        Credentials.from_env(env)


def test_placeholder_values_rejected():
    with pytest.raises(ConfigurationError):
        Credentials.from_env({"FRESHDESK_DOMAIN": "your-domain", "FRESHDESK_API_KEY": "your-api-key"})


@pytest.mark.parametrize(
    "raw,expected",
    [("acme", "acme"), ("ACME.freshdesk.com", "acme"), ("https://acme.freshdesk.com/", "acme")],
)
def test_domain_normalization(raw, expected):
    assert normalize_domain(raw) == expected


@pytest.mark.parametrize("raw", ["evil.com/x", "a b", "", "-x", "acme.example.com", "acme.freshdesk.com.evil.io"])
def test_domain_must_be_plain_freshdesk_subdomain(raw):
    with pytest.raises(ConfigurationError):
        normalize_domain(raw)


def test_api_key_not_in_repr():
    assert "secret" not in repr(Credentials("acme", "secret"))


def test_basic_auth_header_uses_api_key():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers["authorization"]
        return json_response({"id": 1, "status": 2, "priority": 1, "created_at": "2026-10-01T00:00:00Z"})

    service, _, _ = build_service(handler)
    service.get_ticket(1)
    scheme, encoded = seen["auth"].split(" ")
    assert scheme == "Basic"
    assert base64.b64decode(encoded).decode() == "secret:X"


def test_invalid_key_maps_to_structured_error_without_retry():
    service, _, sleeps = build_service(lambda r: json_response({"code": "invalid_credentials"}, 401))
    with pytest.raises(AuthenticationError) as exc:
        service.get_ticket(1)
    assert exc.value.to_dict()["error"]["type"] == "INVALID_CREDENTIALS"
    assert sleeps == []
