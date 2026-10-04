"""Ticket operations: validation, query building, pagination and normalization.

Freshdesk's search API has hard limits (30 results per page, 10 pages) and supports
field filters only, not free text. So:
  * list_tickets maps (page, limit) onto the 30-per-page API windows.
  * search_tickets applies field filters server-side, then matches keywords against
    subject / description / tags over a bounded scan (at most 300 tickets) and reports
    `truncated` when more candidates existed than were scanned.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

from app.freshdesk.client import FreshdeskClient
from app.freshdesk.errors import (
    InvalidRequestError,
    NotFoundError,
    TicketNotFoundError,
    UnexpectedResponseError,
)
from app.models.ticket import Ticket, TicketPage

SEARCH_PAGE_SIZE = 30
SEARCH_MAX_PAGES = 10
SEARCH_MAX_RESULTS = SEARCH_PAGE_SIZE * SEARCH_MAX_PAGES
DEFAULT_LIMIT = 20
MAX_LIMIT = 30
MAX_QUERY_CHARS = 200

STATUS_FILTERS = {
    "open": (2,),
    "pending": (3,),
    "resolved": (4,),
    "closed": (5,),
    "unresolved": (2, 3),
}
PRIORITY_FILTERS = {"low": 1, "medium": 2, "high": 3, "urgent": 4}
STOPWORDS = {
    "a", "an", "the", "of", "for", "to", "in", "on", "with", "and", "or", "about",
    "related", "ticket", "tickets", "all", "any", "show", "find", "me",
}


# ---- validation -----------------------------------------------------------------------

def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_ticket_id(ticket_id: Any) -> int:
    if not _is_int(ticket_id) or ticket_id < 1:
        raise InvalidRequestError("ticket_id must be a positive integer.")
    return ticket_id


def validate_page(page: Any) -> int:
    if not _is_int(page) or page < 1:
        raise InvalidRequestError("page must be an integer >= 1.")
    return page


def validate_limit(limit: Any) -> int:
    if not _is_int(limit) or not 1 <= limit <= MAX_LIMIT:
        raise InvalidRequestError(f"limit must be an integer between 1 and {MAX_LIMIT}.")
    return limit


def resolve_status(status: Any) -> Optional[tuple[int, ...]]:
    if status is None:
        return None
    key = status.strip().lower() if isinstance(status, str) else None
    if key not in STATUS_FILTERS:
        raise InvalidRequestError(f"status must be one of: {', '.join(STATUS_FILTERS)}.")
    return STATUS_FILTERS[key]


def resolve_priority(priority: Any) -> Optional[int]:
    if priority is None:
        return None
    key = priority.strip().lower() if isinstance(priority, str) else None
    if key not in PRIORITY_FILTERS:
        raise InvalidRequestError(f"priority must be one of: {', '.join(PRIORITY_FILTERS)}.")
    return PRIORITY_FILTERS[key]


def parse_date(value: Any, name: str) -> Optional[str]:
    """Accept YYYY-MM-DD or an ISO-8601 datetime; return YYYY-MM-DD."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidRequestError(f"{name} must be a date string like 2026-10-01.")
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        raise InvalidRequestError(f"{name} must be a date string like 2026-10-01.") from None


# ---- query building -------------------------------------------------------------------

def build_api_query(
    statuses: Optional[tuple[int, ...]],
    priority: Optional[int],
    created_after: Optional[str],
    created_before: Optional[str],
) -> str:
    clauses: list[str] = []
    if statuses:
        if len(statuses) == 1:
            clauses.append(f"status:{statuses[0]}")
        else:
            clauses.append("(" + " OR ".join(f"status:{s}" for s in statuses) + ")")
    if priority is not None:
        clauses.append(f"priority:{priority}")
    if created_after:
        clauses.append(f"created_at:>'{created_after}'")
    if created_before:
        clauses.append(f"created_at:<'{created_before}'")
    if not clauses:
        clauses.append("created_at:>'2000-01-01'")
    return '"' + " AND ".join(clauses) + '"'


def _stem(term: str) -> str:
    if len(term) > 5 and term.endswith("ing"):
        return term[:-3]
    if len(term) > 5 and term.endswith("ed"):
        return term[:-2]
    if len(term) > 3 and term.endswith("s"):
        return term[:-1]
    return term


def extract_terms(query: Any) -> list[str]:
    if not isinstance(query, str) or not query.strip():
        raise InvalidRequestError("query must be a non-empty string.")
    if len(query) > MAX_QUERY_CHARS:
        raise InvalidRequestError(f"query must be at most {MAX_QUERY_CHARS} characters.")
    words = re.findall(r"[a-z0-9]+", query.lower())
    terms = [_stem(w) for w in words if w not in STOPWORDS]
    if not terms:
        raise InvalidRequestError("query must contain at least one meaningful search word.")
    return terms


def _matches(raw: Any, terms: list[str]) -> bool:
    if not isinstance(raw, dict):
        return False
    tags = raw.get("tags") if isinstance(raw.get("tags"), list) else []
    parts = [raw.get("subject"), raw.get("description_text"), *tags]
    haystack = " ".join(p for p in parts if isinstance(p, str)).lower()
    return all(term in haystack for term in terms)


# ---- service --------------------------------------------------------------------------

class TicketService:
    def __init__(self, client: FreshdeskClient):
        self._client = client

    def get_ticket(self, ticket_id: Any) -> Ticket:
        ticket_id = validate_ticket_id(ticket_id)
        try:
            raw = self._client.get(f"/tickets/{ticket_id}")
        except NotFoundError:
            raise TicketNotFoundError() from None
        return Ticket.from_api(raw)

    def list_tickets(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        created_after: Optional[str] = None,
        created_before: Optional[str] = None,
        page: int = 1,
        limit: int = DEFAULT_LIMIT,
    ) -> TicketPage:
        statuses = resolve_status(status)
        priority_value = resolve_priority(priority)
        after = parse_date(created_after, "created_after")
        before = parse_date(created_before, "created_before")
        if after and before and after > before:
            raise InvalidRequestError("created_after must not be later than created_before.")
        page = validate_page(page)
        limit = validate_limit(limit)

        query = build_api_query(statuses, priority_value, after, before)
        start = (page - 1) * limit
        end = start + limit
        if end > SEARCH_MAX_RESULTS:
            raise InvalidRequestError(
                f"Freshdesk search only exposes the first {SEARCH_MAX_RESULTS} results; "
                "narrow the filters (e.g. a date range) instead of paging deeper."
            )

        first_api_page = start // SEARCH_PAGE_SIZE + 1
        last_api_page = (end - 1) // SEARCH_PAGE_SIZE + 1
        raws: list[Any] = []
        total: Optional[int] = None
        for api_page in range(first_api_page, last_api_page + 1):
            results, total = self._fetch_search_page(query, api_page)
            raws.extend(results)
            if len(results) < SEARCH_PAGE_SIZE:
                break

        offset = start - (first_api_page - 1) * SEARCH_PAGE_SIZE
        window = raws[offset : offset + limit]
        tickets = [Ticket.from_api(r) for r in window]
        if total is not None:
            has_more = end < min(total, SEARCH_MAX_RESULTS)
        else:
            has_more = len(window) == limit
        return TicketPage(
            tickets=tickets, page=page, limit=limit, count=len(tickets), total=total, has_more=has_more
        )

    def search_tickets(
        self,
        query: str,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        page: int = 1,
        limit: int = DEFAULT_LIMIT,
    ) -> TicketPage:
        terms = extract_terms(query)
        statuses = resolve_status(status)
        priority_value = resolve_priority(priority)
        page = validate_page(page)
        limit = validate_limit(limit)

        api_query = build_api_query(statuses, priority_value, None, None)
        scanned: list[Any] = []
        total = 0
        for api_page in range(1, SEARCH_MAX_PAGES + 1):
            results, reported_total = self._fetch_search_page(api_query, api_page)
            total = reported_total or 0
            scanned.extend(results)
            if len(results) < SEARCH_PAGE_SIZE:
                break

        matched = [Ticket.from_api(r) for r in scanned if _matches(r, terms)]
        matched.sort(key=lambda t: t.created_at, reverse=True)
        start = (page - 1) * limit
        window = matched[start : start + limit]
        return TicketPage(
            tickets=window,
            page=page,
            limit=limit,
            count=len(window),
            total=len(matched),
            has_more=start + limit < len(matched),
            scanned=len(scanned),
            truncated=total > len(scanned),
        )

    def _fetch_search_page(self, query: str, api_page: int) -> tuple[list[Any], Optional[int]]:
        data = self._client.get("/search/tickets", {"query": query, "page": api_page})
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise UnexpectedResponseError("Freshdesk search returned an unexpected payload.")
        total = data.get("total")
        return data["results"], total if isinstance(total, int) else None
