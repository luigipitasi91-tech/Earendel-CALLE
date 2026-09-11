import os
import pytest
from app.calle_adapter import build_result_schema, create_and_wait, evidence_from_calle, readiness
from app.models import Requirement, EvidenceClass

REQS = [
    Requirement(key="date", description="Appointment moved to Friday afternoon"),
    Requirement(key="fee", description="No additional charge"),
]

class FakeCalls:
    def __init__(self): self.kwargs = None
    def create_and_wait(self, **kwargs):
        self.kwargs = kwargs
        return {
            "status": "completed",
            "structured_result": {"date": "yes", "fee": "unknown"},
            "task_completed": True,
            "evidence": ["Appointment moved to Friday afternoon."],
            "summary": "Appointment moved; fee not established.",
        }

class FakeClient:
    last = None
    def __init__(self, api_key, base_url):
        self.api_key = api_key; self.base_url = base_url; self.calls = FakeCalls(); FakeClient.last = self


def test_readiness_requires_api_key(monkeypatch):
    monkeypatch.delenv("CALLE_API_KEY", raising=False)
    assert readiness().mode == "NOT_CONFIGURED"


def test_result_schema_has_unknown_and_is_strict():
    s = build_result_schema(REQS)
    assert s["additionalProperties"] is False
    assert s["properties"]["date"]["enum"] == ["yes", "no", "unknown"]


def test_live_adapter_uses_official_create_and_wait_contract(monkeypatch):
    monkeypatch.setenv("CALLE_API_KEY", "test_key")
    call = create_and_wait(
        task="Reschedule appointment without extra charge",
        phone="+447700900123",
        requirements=REQS,
        metadata={"task_id": "t1"},
        client_factory=FakeClient,
    )
    assert call["status"] == "completed"
    sent = FakeClient.last.calls.kwargs
    assert sent["recipients"][0]["phones"] == ["+447700900123"]
    assert sent["result_schema"]["properties"]["fee"]["enum"][-1] == "unknown"


def test_invalid_phone_is_blocked_before_provider(monkeypatch):
    monkeypatch.setenv("CALLE_API_KEY", "test_key")
    with pytest.raises(ValueError):
        create_and_wait(task="x", phone="07700900123", requirements=REQS, client_factory=FakeClient)


def test_calle_task_completed_does_not_force_verified_evidence():
    call = {
        "status": "completed",
        "task_completed": True,
        "structured_result": {"date": "yes", "fee": "unknown"},
        "evidence": ["Appointment moved."],
    }
    items = evidence_from_calle(call, REQS)
    assert items[0].classification == EvidenceClass.SUPPORTING
    assert items[1].classification == EvidenceClass.NEUTRAL_OR_INSUFFICIENT
