from __future__ import annotations

from typing import Any, Callable, Optional

import httpx

from app.auth.api_key import Credentials
from app.config import Settings
from app.freshdesk.client import FreshdeskClient
from app.freshdesk.tickets import TicketService


def make_raw_ticket(id: int = 1, **overrides: Any) -> dict[str, Any]:
    ticket = {
        "id": id,
        "subject": f"Ticket {id}",
        "description_text": "Customer reports an issue.",
        "status": 2,
        "priority": 3,
        "requester_id": 10,
        "responder_id": None,
        "created_at": "2026-10-01T10:00:00Z",
        "updated_at": "2026-10-02T10:00:00Z",
        "due_by": "2026-10-05T10:00:00Z",
        "tags": [],
    }
    ticket.update(overrides)
    return ticket


def json_response(data: Any, status: int = 200, headers: Optional[dict[str, str]] = None) -> httpx.Response:
    return httpx.Response(status, json=data, headers=headers)


def build_service(
    handler: Callable[[httpx.Request], httpx.Response],
    *,
    max_retries: int = 3,
    limiter: Optional[Any] = None,
):
    """Return (service, client, sleeps). Sleeps are recorded instead of executed."""
    sleeps: list[float] = []
    client = FreshdeskClient(
        Credentials("acme", "secret"),
        Settings(max_retries=max_retries, max_calls_per_minute=10_000),
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
        limiter=limiter,
    )
    return TicketService(client), client, sleeps


def search_handler(tickets: list[dict[str, Any]], total: Optional[int] = None, calls: Optional[list] = None):
    """Mimic Freshdesk search: 30 results per page."""

    def handler(request: httpx.Request) -> httpx.Response:
        if calls is not None:
            calls.append(request)
        page = int(request.url.params["page"])
        chunk = tickets[(page - 1) * 30 : page * 30]
        return json_response({"total": total if total is not None else len(tickets), "results": chunk})

    return handler
