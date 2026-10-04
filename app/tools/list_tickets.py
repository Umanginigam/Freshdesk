from __future__ import annotations

from typing import Any, Optional

from app.freshdesk.tickets import DEFAULT_LIMIT, MAX_LIMIT, TicketService
from app.tools.common import respond

NAME = "list_tickets"
DESCRIPTION = (
    "List Freshdesk tickets using filters (status, priority, creation date range). Read-only. "
    "Use status='unresolved' for open + pending tickets. Results are paginated; "
    "check `has_more` and request the next page if needed."
)
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["open", "pending", "resolved", "closed", "unresolved"]},
        "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
        "created_after": {"type": "string", "description": "Date, e.g. 2026-10-01"},
        "created_before": {"type": "string", "description": "Date, e.g. 2026-10-31"},
        "page": {"type": "integer", "minimum": 1, "default": 1},
        "limit": {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT, "default": DEFAULT_LIMIT},
    },
}


def run(
    service: TicketService,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    page: Any = 1,
    limit: Any = DEFAULT_LIMIT,
) -> dict[str, Any]:
    return respond(
        lambda: service.list_tickets(
            status=status,
            priority=priority,
            created_after=created_after,
            created_before=created_before,
            page=page,
            limit=limit,
        ).model_dump()
    )
