"""Application-level errors.

Every failure that can reach the agent is a ConnectorError subclass with a stable
`type` string. Raw HTTP details and stack traces never leave the connector.
"""

from __future__ import annotations

from typing import Any, Optional


class ConnectorError(Exception):
    type = "CONNECTOR_ERROR"
    default_message = "The connector could not complete the request."

    def __init__(self, message: Optional[str] = None, *, extra: Optional[dict[str, Any]] = None):
        self.message = message or self.default_message
        self.extra = extra or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        error: dict[str, Any] = {"type": self.type, "message": self.message}
        error.update(self.extra)
        return {"success": False, "error": error}


class InternalError(ConnectorError):
    type = "INTERNAL_ERROR"
    default_message = "An unexpected internal error occurred."


class ConfigurationError(ConnectorError):
    type = "CONFIGURATION_ERROR"
    default_message = "The connector is not configured correctly."


class AuthenticationError(ConnectorError):
    type = "INVALID_CREDENTIALS"
    default_message = "Freshdesk rejected the configured API key."


class PermissionDeniedError(ConnectorError):
    type = "FORBIDDEN"
    default_message = "The configured Freshdesk account is not allowed to access this resource."


class NotFoundError(ConnectorError):
    type = "RESOURCE_NOT_FOUND"
    default_message = "The requested resource could not be found."


class TicketNotFoundError(NotFoundError):
    type = "TICKET_NOT_FOUND"
    default_message = "The requested ticket could not be found."


class InvalidRequestError(ConnectorError):
    type = "INVALID_PARAMETERS"
    default_message = "The request parameters are invalid."


class RateLimitedError(ConnectorError):
    type = "RATE_LIMITED"
    default_message = "Freshdesk rate limit reached and retries were exhausted. Try again later."


class ApiTimeoutError(ConnectorError):
    type = "API_TIMEOUT"
    default_message = "Freshdesk did not respond in time."


class NetworkError(ConnectorError):
    type = "NETWORK_ERROR"
    default_message = "Could not reach Freshdesk."


class UpstreamError(ConnectorError):
    type = "UPSTREAM_ERROR"
    default_message = "Freshdesk returned a server error."


class UnexpectedResponseError(ConnectorError):
    type = "UNEXPECTED_RESPONSE"
    default_message = "Freshdesk returned a response the connector could not understand."


class ReadOnlyViolationError(ConnectorError):
    type = "OPERATION_NOT_ALLOWED"
    default_message = "This connector is read-only; the requested operation is not allowed."
