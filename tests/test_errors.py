import httpx
import pytest

from app.auth.api_key import Credentials
from app.config import Settings
from app.freshdesk.client import FreshdeskClient
from app.freshdesk.errors import (
    ApiTimeoutError,
    InvalidRequestError,
    NetworkError,
    PermissionDeniedError,
    ReadOnlyViolationError,
    TicketNotFoundError,
    UnexpectedResponseError,
)
from app.tools import get_ticket
from tests.helpers import build_service, json_response, make_raw_ticket, search_handler


def test_missing_ticket_maps_to_structured_error():
    service, _, _ = build_service(lambda r: json_response({"code": "resource_not_found"}, 404))
    with pytest.raises(TicketNotFoundError) as exc:
        service.get_ticket(999)
    assert exc.value.to_dict() == {
        "success": False,
        "error": {"type": "TICKET_NOT_FOUND", "message": "The requested ticket could not be found."},
    }


def test_forbidden_maps_to_permission_error():
    service, _, _ = build_service(lambda r: json_response({}, 403))
    with pytest.raises(PermissionDeniedError):
        service.get_ticket(1)


@pytest.mark.parametrize("status", [400, 422])
def test_bad_request_surfaces_freshdesk_description(status):
    service, _, _ = build_service(lambda r: json_response({"description": "Validation failed"}, status))
    with pytest.raises(InvalidRequestError) as exc:
        service.get_ticket(1)
    assert "Validation failed" in exc.value.message


def test_timeout_retries_then_reports_api_timeout():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("slow", request=request)

    service, _, sleeps = build_service(handler, max_retries=3)
    with pytest.raises(ApiTimeoutError) as exc:
        service.get_ticket(1)
    assert exc.value.to_dict()["error"]["type"] == "API_TIMEOUT"
    assert len(calls) == 4
    assert sleeps == [0.5, 1.0, 2.0]


def test_timeout_then_success_recovers():
    state = {"n": 0}

    def handler(request):
        state["n"] += 1
        if state["n"] == 1:
            raise httpx.ReadTimeout("slow", request=request)
        return json_response(make_raw_ticket(1))

    service, _, _ = build_service(handler)
    assert service.get_ticket(1).id == 1


def test_network_failure_maps_to_network_error():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    service, _, _ = build_service(handler, max_retries=1)
    with pytest.raises(NetworkError):
        service.get_ticket(1)


def test_non_json_body_is_unexpected_response():
    service, _, _ = build_service(lambda r: httpx.Response(200, content=b"<html>oops</html>"))
    with pytest.raises(UnexpectedResponseError):
        service.get_ticket(1)


def test_ticket_missing_required_fields_is_unexpected_response():
    service, _, _ = build_service(lambda r: json_response({"id": 1, "subject": "no status"}))
    with pytest.raises(UnexpectedResponseError):
        service.get_ticket(1)


def test_search_payload_without_results_list_is_unexpected_response():
    service, _, _ = build_service(lambda r: json_response({"total": 1, "results": "nope"}))
    with pytest.raises(UnexpectedResponseError):
        service.list_tickets()


# ---- read-only boundary ---------------------------------------------------------------

@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE", "post"])
def test_mutating_methods_are_rejected_without_a_request(method):
    def handler(request):
        raise AssertionError("request must never be sent")

    _, client, _ = build_service(handler)
    with pytest.raises(ReadOnlyViolationError) as exc:
        client.request(method, "/tickets/1")
    assert exc.value.type == "OPERATION_NOT_ALLOWED"


@pytest.mark.parametrize(
    "path",
    ["/contacts", "/tickets", "/tickets/1/reply", "/tickets/1/../../agents", "/tickets/abc", "/agents/me"],
)
def test_paths_outside_the_allowlist_are_rejected(path):
    def handler(request):
        raise AssertionError("request must never be sent")

    _, client, _ = build_service(handler)
    with pytest.raises(ReadOnlyViolationError):
        client.get(path)


def test_only_three_read_tools_are_exposed():
    pytest.importorskip("mcp")
    import asyncio

    from app.tools.mcp_server import build_server

    service, _, _ = build_service(search_handler([]))
    tools = asyncio.run(build_server(service).list_tools())
    assert {t.name for t in tools} == {"get_ticket", "list_tickets", "search_tickets"}


def test_unexpected_exceptions_do_not_leak_internals():
    class Broken:
        def get_ticket(self, ticket_id):
            raise RuntimeError("db password is hunter2")

    result = get_ticket.run(Broken(), ticket_id=1)
    assert result["success"] is False
    assert result["error"]["type"] == "INTERNAL_ERROR"
    assert "hunter2" not in str(result)


def test_client_constructs_with_default_settings():
    client = FreshdeskClient(Credentials("acme", "secret"), Settings())
    client.close()
