import pytest

from app.freshdesk.errors import InvalidRequestError
from app.tools import get_ticket, list_tickets
from tests.helpers import build_service, json_response, make_raw_ticket, search_handler


def test_get_ticket_returns_normalized_ticket():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        return json_response(make_raw_ticket(12345, subject="Payment failed"))

    service, _, _ = build_service(handler)
    ticket = service.get_ticket(12345)
    assert seen["path"] == "/api/v2/tickets/12345"
    assert ticket.id == 12345
    assert ticket.status_label == "open"
    assert ticket.priority_label == "high"


@pytest.mark.parametrize("bad_id", [0, -1, "abc", True, None, 1.5])
def test_get_ticket_rejects_invalid_ids_before_any_request(bad_id):
    def handler(request):
        raise AssertionError("no request should be made")

    service, _, _ = build_service(handler)
    with pytest.raises(InvalidRequestError):
        service.get_ticket(bad_id)


def test_unknown_status_gets_generic_label_and_description_is_truncated():
    raw = make_raw_ticket(1, status=99, description_text="x" * 2000)
    service, _, _ = build_service(lambda r: json_response(raw))
    ticket = service.get_ticket(1)
    assert ticket.status_label == "status_99"
    assert len(ticket.description_text) <= 501


def test_tool_get_ticket_success_shape():
    service, _, _ = build_service(lambda r: json_response(make_raw_ticket(7)))
    result = get_ticket.run(service, ticket_id=7)
    assert result["success"] is True
    assert result["ticket"]["id"] == 7


def _capture_query(**kwargs):
    seen = []
    service, _, _ = build_service(search_handler([], calls=seen))
    service.list_tickets(**kwargs)
    return seen[0].url.params["query"]


def test_status_and_priority_filters_build_query():
    assert _capture_query(status="open", priority="high") == '"status:2 AND priority:3"'


def test_unresolved_means_open_or_pending():
    assert _capture_query(status="unresolved") == '"(status:2 OR status:3)"'


def test_date_filters_accept_dates_and_datetimes():
    query = _capture_query(created_after="2026-09-01", created_before="2026-10-01T12:00:00Z")
    assert query == "\"created_at:>'2026-09-01' AND created_at:<'2026-10-01'\""


def test_no_filters_still_valid_query():
    assert _capture_query() == "\"created_at:>'2000-01-01'\""


def test_pagination_maps_onto_30_per_page_api_windows():
    tickets = [make_raw_ticket(i) for i in range(1, 61)]
    calls = []
    service, _, _ = build_service(search_handler(tickets, calls=calls))
    page = service.list_tickets(page=2, limit=20)  # items 21..40 span API pages 1 and 2
    assert [t.id for t in page.tickets] == list(range(21, 41))
    assert len(calls) == 2
    assert page.has_more is True
    assert page.total == 60


def test_last_page_has_no_more():
    tickets = [make_raw_ticket(i) for i in range(1, 26)]
    service, _, _ = build_service(search_handler(tickets))
    page = service.list_tickets(page=2, limit=20)
    assert [t.id for t in page.tickets] == list(range(21, 26))
    assert page.has_more is False


def test_single_api_call_when_window_fits_one_page():
    calls = []
    service, _, _ = build_service(search_handler([make_raw_ticket(i) for i in range(1, 31)], calls=calls))
    service.list_tickets(page=1, limit=10)
    assert len(calls) == 1


def test_paging_beyond_freshdesk_search_cap_is_rejected():
    service, _, _ = build_service(search_handler([]))
    with pytest.raises(InvalidRequestError):
        service.list_tickets(page=11, limit=30)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"status": "bogus"},
        {"priority": "critical"},
        {"limit": 0},
        {"limit": 31},
        {"page": 0},
        {"created_after": "yesterday"},
        {"created_after": "2026-10-05", "created_before": "2026-10-01"},
    ],
)
def test_invalid_list_parameters_rejected(kwargs):
    def handler(request):
        raise AssertionError("no request should be made")

    service, _, _ = build_service(handler)
    with pytest.raises(InvalidRequestError):
        service.list_tickets(**kwargs)


def test_tool_list_tickets_returns_structured_validation_error():
    service, _, _ = build_service(search_handler([]))
    result = list_tickets.run(service, status="nonsense")
    assert result["success"] is False
    assert result["error"]["type"] == "INVALID_PARAMETERS"
