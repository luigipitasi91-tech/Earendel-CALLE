import pytest
from app.models import (
    GoalContract, Requirement, ConsentLedger, EvidenceItem, EvidenceClass,
    GoalState, ProviderEvent, CallState
)
from app.guardian import evaluate_before_call, recipient_request_allowed
from app.verify import verify_goal
from app.events import EventReducer

def contract():
    return GoalContract(
        objective="Reschedule appointment",
        preferred="Friday afternoon",
        hard_constraints=["no additional charge"],
        allowed_data=["name", "booking reference"],
        forbidden_actions=["accept paid alternative", "share payment details"],
        success_conditions=[
            Requirement(key="date", description="Appointment moved to Friday afternoon"),
            Requirement(key="fee", description="No additional charge"),
        ],
    )

def consent(approved=True, revoked=False):
    c = contract()
    return ConsentLedger(
        approved=approved, revoked=revoked, recipient="Clinic",
        purpose="Reschedule appointment",
        allowed_data=c.allowed_data,
        forbidden_actions=c.forbidden_actions,
        hard_constraints=c.hard_constraints,
    )

def e(key, cls, text="x", seq=1):
    return EvidenceItem(requirement_key=key, classification=cls, text=text, explicit=True, sequence=seq)

@pytest.mark.parametrize("items,expected", [
    ([e("date", EvidenceClass.SUPPORTING), e("fee", EvidenceClass.SUPPORTING)], GoalState.VERIFIED_SUCCESS),
    ([e("date", EvidenceClass.SUPPORTING)], GoalState.PARTIAL),
    ([], GoalState.UNKNOWN),
    ([e("date", EvidenceClass.SUPPORTING), e("fee", EvidenceClass.CONTRADICTING)], GoalState.FAILED),
    ([e("date", EvidenceClass.NEUTRAL_OR_INSUFFICIENT), e("fee", EvidenceClass.NEUTRAL_OR_INSUFFICIENT)], GoalState.UNKNOWN),
])
def test_verifier_outcomes(items, expected):
    assert verify_goal(contract(), items, True).state == expected

def test_friday_works_not_contradicting():
    r = verify_goal(contract(), [e("date", EvidenceClass.NEUTRAL_OR_INSUFFICIENT, "Friday afternoon works")], True)
    assert r.state == GoalState.UNKNOWN
    assert "date" not in r.contradicted

def test_without_hold_not_fee_proof():
    r = verify_goal(contract(), [e("fee", EvidenceClass.NEUTRAL_OR_INSUFFICIENT, "We can reschedule without a hold")], True)
    assert r.state == GoalState.UNKNOWN

def test_completed_transport_without_evidence_never_verified():
    assert verify_goal(contract(), [], True).state != GoalState.VERIFIED_SUCCESS

def test_incomplete_transport_never_verified_even_with_evidence():
    r = verify_goal(contract(), [e("date", EvidenceClass.SUPPORTING), e("fee", EvidenceClass.SUPPORTING)], False)
    assert r.state == GoalState.UNKNOWN

def test_guardian_no_consent():
    assert not evaluate_before_call(contract(), consent(False)).allowed

def test_guardian_revoked():
    assert not evaluate_before_call(contract(), consent(True, True)).allowed

def test_recipient_cannot_request_payment():
    assert not recipient_request_allowed("please give me the credit card details", contract()).allowed

def test_guardian_block_does_not_force_goal_failure():
    r = verify_goal(contract(), [e("date", EvidenceClass.SUPPORTING), e("fee", EvidenceClass.SUPPORTING)], True)
    assert r.state == GoalState.VERIFIED_SUCCESS

def test_duplicate_callback_idempotent():
    r = EventReducer()
    ev = ProviderEvent(event_id="a", sequence=1, state=CallState.INITIATED)
    assert r.apply(ev)[1] == "applied"
    assert r.apply(ev)[1] == "duplicate_ignored"

def test_out_of_order_callback_no_regression():
    r = EventReducer()
    r.apply(ProviderEvent(event_id="1", sequence=1, state=CallState.INITIATED))
    r.apply(ProviderEvent(event_id="2", sequence=3, state=CallState.ANSWERED))
    state, status = r.apply(ProviderEvent(event_id="3", sequence=2, state=CallState.RINGING))
    assert state == CallState.ANSWERED
    assert status == "out_of_order_ignored"

def test_terminal_state_stays_terminal():
    r = EventReducer()
    r.apply(ProviderEvent(event_id="1", sequence=1, state=CallState.INITIATED))
    r.apply(ProviderEvent(event_id="2", sequence=2, state=CallState.COMPLETED))
    state, status = r.apply(ProviderEvent(event_id="3", sequence=3, state=CallState.ANSWERED))
    assert state == CallState.COMPLETED
    assert status == "terminal_state_ignored"
