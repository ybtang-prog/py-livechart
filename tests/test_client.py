import time

import pytest

from py_livechart import (
    GroundStateRecord,
    LiveChartClient,
    NoDataFoundError,
    RateLimitExceededError,
)


class DummyResponse:
    def __init__(self, text: str, status_code: int = 200, reason: str = "OK"):
        self.text = text
        self.status_code = status_code
        self.reason = reason


class DummySession:
    def __init__(self, response: DummyResponse):
        self._response = response
        self.headers = {}

    def mount(self, *_args, **_kwargs):
        return None

    def get(self, *_args, **_kwargs):
        return self._response


def test_get_ground_states_records():
    csv = "symbol,a,z,n,half_life_sec\nCo-60,60,27,33,1.62e8\n"
    session = DummySession(DummyResponse(csv))
    client = LiveChartClient(rate_limit_per_sec=0, session_factory=lambda: session)

    records = client.get_ground_states("60co", return_type="records")
    assert isinstance(records[0], GroundStateRecord)
    assert records[0].mass_number == 60


def test_rate_limiter_raises_when_timeout_elapsed(monkeypatch):
    # Force rate limiter into zero-capacity state by sleeping token bucket.
    csv = "symbol,a,z,n,half_life_sec\nCo-60,60,27,33,1.62e8\n"
    session = DummySession(DummyResponse(csv))
    client = LiveChartClient(
        rate_limit_per_sec=0.0001, burst_size=1, timeout=0.01, session_factory=lambda: session
    )

    # First call consumes the only token.
    client.get_ground_states("60co")

    with monkeypatch.context() as m:
        # Patch time.sleep to avoid waiting during the test
        m.setattr(time, "sleep", lambda _x: None)
        with pytest.raises(RateLimitExceededError):
            client.get_ground_states("60co")


def test_fetch_ground_states_many_handles_errors(monkeypatch):
    client = LiveChartClient(rate_limit_per_sec=0)

    def fake_get(nuclide, return_type="dataframe"):
        if nuclide == "bad":
            raise NoDataFoundError("No data")
        return {"nuclide": nuclide, "return_type": return_type}

    monkeypatch.setattr(client, "get_ground_states", fake_get)

    results, errors = client.fetch_ground_states_many(
        ["60co", "bad", "60co"], return_type="records", max_workers=2
    )

    assert "60co" in results
    assert "bad" in errors
    assert results["60co"]["return_type"] == "records"


def test_fetch_ground_states_many_raise_on_error(monkeypatch):
    client = LiveChartClient(rate_limit_per_sec=0)

    def fake_get(_nuclide, return_type="dataframe"):
        raise NoDataFoundError("boom")

    monkeypatch.setattr(client, "get_ground_states", fake_get)

    with pytest.raises(NoDataFoundError):
        client.fetch_ground_states_many(["60co"], raise_on_error=True)

