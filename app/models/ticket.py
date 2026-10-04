"""Agent-friendly ticket models (data minimization: only the fields the agent needs)."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ValidationError

from app.freshdesk.errors import UnexpectedResponseError

STATUS_LABELS = {2: "open", 3: "pending", 4: "resolved", 5: "closed"}
PRIORITY_LABELS = {1: "low", 2: "medium", 3: "high", 4: "urgent"}
MAX_DESCRIPTION_CHARS = 500


class Ticket(BaseModel):
    id: int
    subject: str
    status: int
    status_label: str
    priority: int
    priority_label: str
    description_text: Optional[str] = None
    requester_id: Optional[int] = None
    responder_id: Optional[int] = None
    created_at: str
    updated_at: Optional[str] = None
    due_by: Optional[str] = None
    tags: list[str] = []

    @classmethod
    def from_api(cls, raw: Any) -> "Ticket":
        if not isinstance(raw, dict):
            raise UnexpectedResponseError("Freshdesk returned a malformed ticket.")
        try:
            status = raw["status"]
            priority = raw["priority"]
            description = raw.get("description_text")
            if isinstance(description, str) and len(description) > MAX_DESCRIPTION_CHARS:
                description = description[:MAX_DESCRIPTION_CHARS].rstrip() + "…"
            return cls(
                id=raw["id"],
                subject=raw.get("subject") or "",
                status=status,
                status_label=STATUS_LABELS.get(status, f"status_{status}"),
                priority=priority,
                priority_label=PRIORITY_LABELS.get(priority, f"priority_{priority}"),
                description_text=description,
                requester_id=raw.get("requester_id"),
                responder_id=raw.get("responder_id"),
                created_at=raw["created_at"],
                updated_at=raw.get("updated_at"),
                due_by=raw.get("due_by"),
                tags=raw.get("tags") or [],
            )
        except (KeyError, TypeError, ValidationError):
            raise UnexpectedResponseError("Freshdesk returned a ticket with missing or invalid fields.") from None


class TicketPage(BaseModel):
    tickets: list[Ticket]
    page: int
    limit: int
    count: int
    total: Optional[int] = None
    has_more: bool = False
    scanned: Optional[int] = None
    truncated: bool = False
