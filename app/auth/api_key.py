"""Freshdesk API-key authentication.

Freshdesk uses HTTP Basic auth with the API key as username and any string as password.
Credentials come from environment variables only and are never logged or shown in repr().
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Mapping, Optional

import httpx

from app.freshdesk.errors import ConfigurationError

_SUBDOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_PLACEHOLDERS = {"your-api-key", "your-domain"}


def normalize_domain(raw: str) -> str:
    """Accept 'acme', 'acme.freshdesk.com' or a full URL; return the bare subdomain.

    Restricting to a plain subdomain guarantees requests only go to *.freshdesk.com.
    """
    value = (raw or "").strip().lower()
    value = re.sub(r"^https?://", "", value).rstrip("/")
    if value.endswith(".freshdesk.com"):
        value = value[: -len(".freshdesk.com")]
    if value in _PLACEHOLDERS or not _SUBDOMAIN_RE.match(value):
        raise ConfigurationError(
            "FRESHDESK_DOMAIN must be your Freshdesk subdomain, e.g. 'acme' for acme.freshdesk.com."
        )
    return value


@dataclass(frozen=True)
class Credentials:
    domain: str
    api_key: str = field(repr=False)

    def __post_init__(self):
        object.__setattr__(self, "domain", normalize_domain(self.domain))
        key = (self.api_key or "").strip()
        if not key or key in _PLACEHOLDERS:
            raise ConfigurationError("FRESHDESK_API_KEY is not set.")
        object.__setattr__(self, "api_key", key)

    @property
    def base_url(self) -> str:
        return f"https://{self.domain}.freshdesk.com/api/v2"

    @property
    def auth(self) -> httpx.BasicAuth:
        return httpx.BasicAuth(self.api_key, "X")

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "Credentials":
        env = os.environ if env is None else env
        return cls(domain=env.get("FRESHDESK_DOMAIN", ""), api_key=env.get("FRESHDESK_API_KEY", ""))
