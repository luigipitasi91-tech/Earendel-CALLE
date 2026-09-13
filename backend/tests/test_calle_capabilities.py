from fastapi.testclient import TestClient

from app.calle_capabilities import check_route
from app.main import CALL_JOBS, app


client = TestClient(app)
CONTRACT = {
    "goal": "Reschedule appointment",
    "hard_constraints": ["No additional charge"],
    "allowed_data": ["name"],
    "forbidden_actions": ["share payment details"],
    "success_requirements": [
        {"id": "appointment", "text": "Appointment moved", "evidence_keywords": ["moved"]}
    ],
}


def _authorized_task() -> str:
    created = client.post("/tasks", json={"intent": "Move appointment", "recipient": "Clinic", "contract": CONTRACT})
    task_id = created.json()["task_id"]
    consent = client.post("/consent", json={
        "task_id": task_id,
        "recipient": "Clinic",
        "purpose": "Move appointment",
        "allowed_data": ["name"],
        "forbidden_actions": ["share payment details"],
        "constraints": ["No additional charge"],
        "approved": True,
    })
    assert consent.status_code == 200
    return task_id


def test_canonical_us_route_and_number_are_allowed(monkeypatch):
    monkeypatch.setenv("CALLE_ENABLED_ROUTES", "US:en-US")
    allowed, reason = check_route(phone="+14155550100", region="US", locale="en-US")
    assert allowed is True
    assert "controlled live trial" in reason


def test_known_gb_runtime_rejection_is_blocked():
    allowed, reason = check_route(phone="+447911123456", region="GB", locale="en-GB")
    assert allowed is False
    assert "currently rejects GB/en-GB" in reason


def test_number_must_resolve_to_selected_region(monkeypatch):
    monkeypatch.setenv("CALLE_ENABLED_ROUTES", "US:en-US")
    allowed, reason = check_route(phone="+442071838750", region="US", locale="en-US")
    assert allowed is False
    assert "resolves to GB, not US" in reason


def test_unsupported_route_is_rejected_before_provider_job(monkeypatch):
    monkeypatch.setenv("CALLE_API_KEY", "test-key")
    task_id = _authorized_task()
    jobs_before = set(CALL_JOBS)
    response = client.post("/calls/calle/start", json={
        "task_id": task_id,
        "phone": "+442071838750",
        "region": "GB",
        "locale": "en-GB",
    })
    assert response.status_code == 422
    assert set(CALL_JOBS) == jobs_before


def test_readiness_exposes_only_server_controlled_routes(monkeypatch):
    monkeypatch.setenv("CALLE_ENABLED_ROUTES", "US:en-US,GB:en-GB")
    body = client.get("/calle/readiness").json()
    assert body["runtime_route_guaranteed"] is False
    assert [(route["region"], route["locale"]) for route in body["controlled_live_routes"]] == [("US", "en-US")]
