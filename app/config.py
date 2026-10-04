"""Runtime tuning read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Mapping, Optional

from app.freshdesk.errors import ConfigurationError


def _read(env: Mapping[str, str], name: str, default, cast: Callable, minimum):
    raw = env.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = cast(raw)
    except ValueError:
        raise ConfigurationError(f"{name} must be a number.") from None
    if value < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}.")
    return value


@dataclass(frozen=True)
class Settings:
    timeout_seconds: float = 10.0
    max_retries: int = 3
    max_calls_per_minute: int = 100

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "Settings":
        env = os.environ if env is None else env
        return cls(
            timeout_seconds=_read(env, "FRESHDESK_TIMEOUT_SECONDS", 10.0, float, 0.1),
            max_retries=_read(env, "FRESHDESK_MAX_RETRIES", 3, int, 0),
            max_calls_per_minute=_read(env, "FRESHDESK_MAX_CALLS_PER_MINUTE", 100, int, 1),
        )
