from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

CONTRACT = {
    "goal": "Reschedule appointment",
    "preferred": "Friday afternoon",
    "hard_constraints": ["No additional charge"],
    "allowed_data": ["name", "booking reference"],
    "forbidden_actions": ["accept paid alternative", "share payment details"],
    "success_requirements": [
        {"id": "appointment", "text": "Appointment moved to Friday", "evidence_keywords": ["friday"]},
        {"id": "fee", "text": "No additional charge", "evidence_keywords": ["no additional charge"]},
    ],
}


def create_and_consent():
    r = client.post("/tasks", json={"intent": "Move my appointment to Friday afternoon only if free", "recipient": "Clinic", "contract": CONTRACT})
    assert r.status_code == 200
    task_id = r.json()["task_id"]
    c = client.post("/consent", json={
        "task_id": task_id,
        "recipient": "Clinic",
        "purpose": "Reschedule appointment",
        "allowed_data": ["name", "booking reference"],
        "forbidden_actions": ["accept paid alternative", "share payment details"],
        "constraints": ["No additional charge"],
        "approved": True,
    })
    assert c.status_code == 200
    return task_id


def test_verified_success():
    task_id = create_and_consent()
    r = client.post("/calls/simulate", json={"task_id": task_id, "transcript": "Yes, your appointment is now Friday at 14:30. There is no additional charge."})
    assert r.status_code == 200
    assert r.json()["goal_state"] == "VERIFIED_SUCCESS"


def test_partial_success_does_not_overclaim():
    task_id = create_and_consent()
    r = client.post("/calls/simulate", json={"task_id": task_id, "transcript": "Yes, your appointment is now Friday at 14:30."})
    assert r.status_code == 200
    assert r.json()["goal_state"] == "PARTIAL"


def test_unknown_when_no_evidence():
    task_id = create_and_consent()
    r = client.post("/calls/simulate", json={"task_id": task_id, "transcript": "We will look into this and get back to you."})
    assert r.status_code == 200
    assert r.json()["goal_state"] == "UNKNOWN"


def test_execution_requires_consent():
    r = client.post("/tasks", json={"intent": "Move appointment", "recipient": "Clinic", "contract": CONTRACT})
    task_id = r.json()["task_id"]
    x = client.post("/calls/simulate", json={"task_id": task_id, "transcript": "Friday confirmed."})
    assert x.status_code == 403


def test_feedback_stars_validation():
    task_id = create_and_consent()
    bad = client.post("/feedback", json={"task_id": task_id, "stars": 6, "comment": "x"})
    assert bad.status_code == 422
    ok = client.post("/feedback", json={"task_id": task_id, "stars": 5, "comment": "Clear and useful"})
    assert ok.status_code == 200
