"""Shared helper that turns any outcome into a structured tool response."""

from __future__ import annotations

import logging
from typing import Any, Callable

from app.freshdesk.errors import ConnectorError, InternalError

logger = logging.getLogger(__name__)


def respond(fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Run `fn`; return {"success": True, ...} or a structured error. Never raises."""
    try:
        return {"success": True, **fn()}
    except ConnectorError as exc:
        return exc.to_dict()
    except Exception:  # noqa: BLE001 - last line of defence; details go to logs, not the agent
        logger.exception("Unexpected error in tool call")
        return InternalError().to_dict()
