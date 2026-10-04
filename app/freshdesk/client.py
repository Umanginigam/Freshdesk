"""Low-level, read-only Freshdesk HTTP client.

Only GET requests to an explicit allowlist of paths are possible. Auth, rate limiting,
retries and HTTP-to-application error mapping all live here.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Callable, Optional

import httpx

from app.auth.api_key import Credentials
from app.config import Settings
from app.freshdesk.errors import (
    AuthenticationError,
    InvalidRequestError,
    NotFoundError,
    PermissionDeniedError,
    ReadOnlyViolationError,
    UnexpectedResponseError,
    UpstreamError,
)
from app.middleware.rate_limiter import RateLimiter
from app.middleware.retry import send_with_retries

logger = logging.getLogger(__name__)

ALLOWED_PATHS = (
    re.compile(r"^/tickets/\d+$"),
    re.compile(r"^/search/tickets$"),
)


class FreshdeskClient:
    def __init__(
        self,
        credentials: Credentials,
        settings: Optional[Settings] = None,
        *,
        transport: Optional[httpx.BaseTransport] = None,
        sleep: Callable[[float], None] = time.sleep,
        limiter: Optional[Any] = None,
    ):
        self._settings = settings or Settings()
        self._sleep = sleep
        self._limiter = limiter or RateLimiter(self._settings.max_calls_per_minute)
        self._http = httpx.Client(
            base_url=credentials.base_url,
            auth=credentials.auth,
            timeout=self._settings.timeout_seconds,
            headers={"Accept": "application/json"},
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def get(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        return self.request("GET", path, params)

    def request(self, method: str, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        if method.upper() != "GET":
            raise ReadOnlyViolationError()
        if not any(pattern.match(path) for pattern in ALLOWED_PATHS):
            raise ReadOnlyViolationError("This Freshdesk endpoint is not exposed by the connector.")

        def send() -> httpx.Response:
            self._limiter.acquire()
            return self._http.get(path, params=params)

        response = send_with_retries(send, max_retries=self._settings.max_retries, sleep=self._sleep)
        logger.debug("GET %s -> %s", path, response.status_code)
        return self._parse(response)

    @staticmethod
    def _parse(response: httpx.Response) -> Any:
        code = response.status_code
        if 200 <= code < 300:
            try:
                return response.json()
            except ValueError:
                raise UnexpectedResponseError("Freshdesk returned a non-JSON response.") from None
        if code == 401:
            raise AuthenticationError()
        if code == 403:
            raise PermissionDeniedError()
        if code == 404:
            raise NotFoundError()
        if code in (400, 422):
            raise InvalidRequestError(_upstream_message(response))
        raise UpstreamError(f"Freshdesk returned HTTP {code}.")


def _upstream_message(response: httpx.Response) -> str:
    try:
        description = response.json().get("description")
    except (ValueError, AttributeError):
        description = None
    if isinstance(description, str) and description:
        return f"Freshdesk rejected the request: {description[:200]}"
    return "Freshdesk rejected the request parameters."
