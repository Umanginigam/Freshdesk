from __future__ import annotations

from typing import Any

from app.freshdesk.tickets import TicketService
from app.tools.common import respond

NAME = "get_ticket"
DESCRIPTION = (
    "Retrieve a single Freshdesk ticket by its numeric ID. Read-only. "
    "Returns subject, status, priority, timestamps and a short description."
)
INPUT_SCHEMA = {
    "type": "object",
    "properties": {"ticket_id": {"type": "integer", "description": "Freshdesk ticket ID"}},
    "required": ["ticket_id"],
}


def run(service: TicketService, ticket_id: Any) -> dict[str, Any]:
    return respond(lambda: {"ticket": service.get_ticket(ticket_id).model_dump()})
