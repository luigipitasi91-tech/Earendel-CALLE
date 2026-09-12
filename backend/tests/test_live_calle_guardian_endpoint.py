from fastapi.testclient import TestClient
from app.main import app
import app.main as main

client = TestClient(app)
CONTRACT = {
    "goal": "Reschedule appointment",
    "hard_constraints": ["No additional charge"],
    "allowed_data": ["name"],
    "forbidden_actions": ["share payment details", "accept paid alternative"],
    "success_requirements": [
        {"id": "date", "text": "Appointment moved to Friday"},
        {"id": "fee", "text": "No additional charge"},
    ],
}


def setup_task():
    t = client.post(
        "/tasks",
        json={"intent": "Move appointment to Friday only if free", "recipient": "Clinic", "contract": CONTRACT},
    ).json()["task_id"]
    client.post(
        "/consent",
        json={
            "task_id": t,
            "recipient": "Clinic",
            "purpose": "Reschedule",
            "allowed_data": ["name"],
            "forbidden_actions": ["share payment details", "accept paid alternative"],
            "constraints": ["No additional charge"],
            "approved": True,
        },
    )
    return t


def test_live_endpoint_marks_guardian_block_and_refuses_verified_success(monkeypatch):
    t = setup_task()

    class Ready:
        configured = True

    monkeypatch.setattr(main, "calle_readiness", lambda: Ready())
    monkeypatch.setattr(
        main,
        "calle_create_and_wait",
        lambda **kwargs: {
            "id": "c1",
            "status": "completed",
            "task_completed": True,
            "structured_result": {"date": "yes", "fee": "yes"},
            "summary": "Appointment moved to Friday; payment was made and the fee was accepted.",
            "evidence": ["Appointment moved to Friday."],
        },
    )
    r = client.post("/calls/calle/live", json={"task_id": t, "phone": "+447700900123"})
    assert r.status_code == 200
    body = r.json()
    assert body["guardian"] == "BLOCKED"
    assert body["goal_state"] == "FAILED"
    assert body["verified"] == ["date"]
    assert "fee" in body["contradicted"]
    assert body["provider_task_completed"] is True
