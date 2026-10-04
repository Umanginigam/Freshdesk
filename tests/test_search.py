import pytest

from app.freshdesk.errors import InvalidRequestError
from app.tools import search_tickets
from tests.helpers import build_service, make_raw_ticket, search_handler

TICKETS = [
    make_raw_ticket(1, subject="Payment failed at checkout", created_at="2026-10-01T10:00:00Z"),
    make_raw_ticket(2, subject="Refund request", created_at="2026-10-02T10:00:00Z"),
    make_raw_ticket(3, subject="Invoice", description_text="Card payment failure on invoice", created_at="2026-10-03T10:00:00Z"),
    make_raw_ticket(4, subject="Login help", tags=["Payments", "failed"], created_at="2026-10-04T10:00:00Z"),
]


def test_keyword_search_matches_subject_description_and_tags_newest_first():
    service, _, _ = build_service(search_handler(TICKETS))
    page = service.search_tickets("failed payments")
    assert [t.id for t in page.tickets] == [4, 3, 1]


def test_search_is_case_insensitive():
    service, _, _ = build_service(search_handler(TICKETS))
    assert [t.id for t in service.search_tickets("REFUND").tickets] == [2]


def test_all_terms_required():
    service, _, _ = build_service(search_handler(TICKETS))
    assert service.search_tickets("failed refund").tickets == []


def test_status_and_priority_are_pushed_down_to_freshdesk():
    calls = []
    service, _, _ = build_service(search_handler(TICKETS, calls=calls))
    service.search_tickets("payment", status="unresolved", priority="high")
    assert calls[0].url.params["query"] == '"(status:2 OR status:3) AND priority:3"'


@pytest.mark.parametrize("query", ["", "   ", "the and of", None, 123, "x" * 201])
def test_bad_queries_rejected(query):
    service, _, _ = build_service(search_handler(TICKETS))
    with pytest.raises(InvalidRequestError):
        service.search_tickets(query)


def test_local_pagination_over_matches():
    tickets = [make_raw_ticket(i, subject="payment failed", created_at=f"2026-09-{(i % 28) + 1:02d}T00:00:00Z") for i in range(1, 26)]
    service, _, _ = build_service(search_handler(tickets))
    page1 = service.search_tickets("payment", limit=10, page=1)
    page3 = service.search_tickets("payment", limit=10, page=3)
    assert page1.count == 10 and page1.has_more is True
    assert page3.count == 5 and page3.has_more is False
    assert page1.total == 25


def test_scan_is_bounded_and_reports_truncation():
    tickets = [make_raw_ticket(i, subject="payment failed") for i in range(1, 301)]
    calls = []
    service, _, _ = build_service(search_handler(tickets, total=500, calls=calls))
    page = service.search_tickets("payment")
    assert len(calls) == 10
    assert page.scanned == 300
    assert page.truncated is True


def test_no_truncation_flag_when_everything_scanned():
    service, _, _ = build_service(search_handler(TICKETS))
    page = service.search_tickets("payment")
    assert page.scanned == 4
    assert page.truncated is False


def test_tool_wrapper_returns_structured_error_for_bad_input():
    service, _, _ = build_service(search_handler(TICKETS))
    result = search_tickets.run(service, query="")
    assert result["success"] is False
    assert result["error"]["type"] == "INVALID_PARAMETERS"
