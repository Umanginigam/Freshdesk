import httpx
import pytest

from app.freshdesk.errors import RateLimitedError, UpstreamError
from app.middleware.rate_limiter import RateLimiter
from tests.helpers import build_service, json_response, make_raw_ticket


def sequence(*responses):
    """Handler returning the given responses in order; records call count."""
    state = {"calls": 0}

    def handler(request):
        response = responses[min(state["calls"], len(responses) - 1)]
        state["calls"] += 1
        return response

    handler.state = state
    return handler


def limited(retry_after=None):
    headers = {"Retry-After": retry_after} if retry_after is not None else None
    return httpx.Response(429, json={"message": "rate limit"}, headers=headers)


def test_retry_after_header_is_honoured():
    handler = sequence(limited("2"), json_response(make_raw_ticket(1)))
    service, _, sleeps = build_service(handler)
    assert service.get_ticket(1).id == 1
    assert sleeps == [2.0]


def test_exponential_backoff_without_header():
    handler = sequence(limited(), limited(), limited(), json_response(make_raw_ticket(1)))
    service, _, sleeps = build_service(handler)
    service.get_ticket(1)
    assert sleeps == [0.5, 1.0, 2.0]


def test_retry_after_is_capped():
    handler = sequence(limited("9999"), json_response(make_raw_ticket(1)))
    service, _, sleeps = build_service(handler)
    service.get_ticket(1)
    assert sleeps == [30.0]


def test_gives_up_after_max_retries_with_structured_error():
    handler = sequence(limited("1"))
    service, _, sleeps = build_service(handler, max_retries=2)
    with pytest.raises(RateLimitedError) as exc:
        service.get_ticket(1)
    assert handler.state["calls"] == 3
    assert len(sleeps) == 2
    error = exc.value.to_dict()["error"]
    assert error["type"] == "RATE_LIMITED"
    assert error["retry_after_seconds"] == 1.0


def test_transient_5xx_is_retried():
    handler = sequence(httpx.Response(503), json_response(make_raw_ticket(1)))
    service, _, sleeps = build_service(handler)
    assert service.get_ticket(1).id == 1
    assert sleeps == [0.5]


def test_persistent_5xx_becomes_upstream_error():
    handler = sequence(httpx.Response(502))
    service, _, _ = build_service(handler, max_retries=1)
    with pytest.raises(UpstreamError):
        service.get_ticket(1)
    assert handler.state["calls"] == 2


def test_client_acquires_limiter_before_each_attempt():
    class CountingLimiter:
        count = 0

        def acquire(self):
            self.count += 1

    limiter = CountingLimiter()
    handler = sequence(limited("0"), json_response(make_raw_ticket(1)))
    service, _, _ = build_service(handler, limiter=limiter)
    service.get_ticket(1)
    assert limiter.count == 2


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.slept = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def test_rate_limiter_blocks_when_budget_exhausted():
    clock = FakeClock()
    limiter = RateLimiter(2, period=60, clock=clock, sleep=clock.sleep)
    limiter.acquire()
    limiter.acquire()
    assert clock.slept == []
    limiter.acquire()  # third call inside the window must wait for the oldest to expire
    assert clock.slept == [60.0]


def test_rate_limiter_window_slides():
    clock = FakeClock()
    limiter = RateLimiter(1, period=10, clock=clock, sleep=clock.sleep)
    limiter.acquire()
    clock.now = 11.0
    limiter.acquire()
    assert clock.slept == []


@pytest.mark.parametrize("kwargs", [{"max_calls": 0}, {"max_calls": 1, "period": 0}])
def test_rate_limiter_validates_arguments(kwargs):
    with pytest.raises(ValueError):
        RateLimiter(**kwargs)
