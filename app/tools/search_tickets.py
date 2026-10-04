from __future__ import annotations

from typing import Any, Optional

from app.freshdesk.tickets import DEFAULT_LIMIT, MAX_LIMIT, TicketService
from app.tools.common import respond

NAME = "search_tickets"
DESCRIPTION = (
    "Search Freshdesk tickets by keywords (matched against subject, description and tags; "
    "all keywords must match), optionally filtered by status and priority. Read-only. "
    "Scans at most 300 tickets; if `truncated` is true, narrow with status/priority."
)
INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Keywords, e.g. 'failed payment'"},
        "status": {"type": "string", "enum": ["open", "pending", "resolved", "closed", "unresolved"]},
        "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
        "page": {"type": "integer", "minimum": 1, "default": 1},
        "limit": {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT, "default": DEFAULT_LIMIT},
    },
    "required": ["query"],
}


def run(
    service: TicketService,
    query: Any,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    page: Any = 1,
    limit: Any = DEFAULT_LIMIT,
) -> dict[str, Any]:
    return respond(
        lambda: service.search_tickets(
            query=query, status=status, priority=priority, page=page, limit=limit
        ).model_dump()
    )
