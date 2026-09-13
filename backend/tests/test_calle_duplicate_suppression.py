from app import calle_adapter as ca
from app.models import Requirement

REQS = [Requirement(key="appointment", description="Appointment moved to Friday 18 September 2026")]


class CountingCalls:
    count = 0

    def create_and_wait(self, **kwargs):
        CountingCalls.count += 1
        return {
            "id": "call_once",
            "status": "completed",
            "task_completed": True,
            "structured_result": {"appointment": "yes"},
            "evidence": ["Appointment moved."],
        }


class CountingClient:
    def __init__(self, api_key, base_url):
        self.calls = CountingCalls()


def test_identical_live_provider_request_runs_only_once(monkeypatch):
    monkeypatch.setenv("CALLE_API_KEY", "test_key")
    ca._CALL_DEDUPE_RECENT.clear()
    ca._CALL_DEDUPE_INFLIGHT.clear()
    CountingCalls.count = 0

    kwargs = dict(
        task="Move appointment to Friday 18 September 2026",
        phone="+12185550123",
        requirements=REQS,
        region="US",
        locale="en-US",
        client_factory=CountingClient,
    )
    first = ca.create_and_wait(**kwargs)
    second = ca.create_and_wait(**kwargs)

    assert first["id"] == "call_once"
    assert second["id"] == "call_once"
    assert CountingCalls.count == 1
