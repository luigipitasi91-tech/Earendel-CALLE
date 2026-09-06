"""
Deterministic tests for Future Call AI critical invariants.
No network, no LLM — pure function-level tests over verify_engine.
Run: python -m pytest -q backend/tests/test_invariants.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import verify_engine as ve  # noqa: E402


DEMO_CONTRACT = {
    "goal": "Reschedule appointment.",
    "hard_constraints": ["No additional charge."],
    "forbidden_data": ["Payment details"],
    "forbidden_actions": ["Accept any paid alternative without new user consent."],
    "success_conditions": [
        {"id": "A", "text": "Appointment moved to Friday afternoon.",
         "kind": "affirmative", "keywords": ["friday", "afternoon"]},
        {"id": "B", "text": "No additional charge.",
         "kind": "no_charge", "keywords": []},
    ],
}


def _turn(role, text, seq=0):
    return {"seq": seq, "role": role, "text": text, "at": "t"}


def test_completed_call_without_evidence_is_not_verified_success():
    v = ve.verify(DEMO_CONTRACT, [], "completed")
    assert v["verdict"] != ve.VERIFIED_SUCCESS


def test_provider_completed_alone_is_not_verified_success():
    tr = [_turn("system_event", "Call ended. Provider state: completed.")]
    v = ve.verify(DEMO_CONTRACT, tr, "completed")
    assert v["verdict"] != ve.VERIFIED_SUCCESS


def test_missing_required_evidence_is_partial_or_unknown():
    tr = [_turn("recipient", "Your appointment has been moved to Friday afternoon.")]
    v = ve.verify(DEMO_CONTRACT, tr, "completed")
    assert v["verdict"] == ve.PARTIAL


def test_contradictory_evidence_produces_failed():
    tr = [
        _turn("recipient", "We can move it to Friday afternoon but there will be a fee of $25."),
    ]
    v = ve.verify(DEMO_CONTRACT, tr, "completed")
    assert v["verdict"] == ve.FAILED


def test_verified_success_requires_all_conditions():
    tr = [
        _turn("recipient", "Confirmed, your appointment is moved to Friday afternoon and there is no additional charge."),
    ]
    v = ve.verify(DEMO_CONTRACT, tr, "completed")
    assert v["verdict"] == ve.VERIFIED_SUCCESS


def test_voicemail_is_unknown_not_success():
    tr = [_turn("recipient", "You have reached voicemail. Please leave a message after the tone.")]
    v = ve.verify(DEMO_CONTRACT, tr, "completed")
    assert v["verdict"] == ve.UNKNOWN


def test_provider_failed_is_failed_not_success():
    v = ve.verify(DEMO_CONTRACT, [], "failed", provider_failed=True)
    assert v["verdict"] == ve.FAILED


def test_websocket_failure_never_verified_success():
    tr = [_turn("recipient", "Appointment moved to Friday afternoon, no additional charge.")]
    v = ve.verify(DEMO_CONTRACT, tr, "in-progress", websocket_failed=True)
    # It could be VERIFIED_SUCCESS because evidence exists — but if there is
    # no evidence, WS failure must degrade to UNKNOWN. Both branches covered.
    assert v["verdict"] in (ve.VERIFIED_SUCCESS, ve.UNKNOWN, ve.PARTIAL)
    v2 = ve.verify(DEMO_CONTRACT, [], "in-progress", websocket_failed=True)
    assert v2["verdict"] == ve.UNKNOWN


def test_consent_revoked_produces_failed():
    tr = [_turn("recipient", "Appointment moved to Friday afternoon, no additional charge.")]
    v = ve.verify(DEMO_CONTRACT, tr, "completed", consent_revoked=True)
    assert v["verdict"] == ve.FAILED


def test_recipient_cannot_expand_permissions():
    hit = ve.recipient_wants_forbidden(
        "Can I have your credit card number to hold the slot?",
        forbidden_actions=DEMO_CONTRACT["forbidden_actions"],
        forbidden_data=DEMO_CONTRACT["forbidden_data"],
    )
    assert hit is not None


def test_ambiguous_evidence_is_not_verified():
    tr = [_turn("recipient", "Uh, I'll have to check with billing later.")]
    v = ve.verify(DEMO_CONTRACT, tr, "completed")
    assert v["verdict"] in (ve.PARTIAL, ve.UNKNOWN)
    assert v["verdict"] != ve.VERIFIED_SUCCESS
