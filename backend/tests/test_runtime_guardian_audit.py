from app.runtime_guardian import audit_provider_result
from app.models import GoalContract, Requirement, ConsentLedger, EvidenceClass

CONTRACT=GoalContract(objective="Reschedule",hard_constraints=["No additional charge"],allowed_data=["name"],forbidden_actions=["share payment details","accept paid alternative"],success_conditions=[Requirement(key="date",description="Appointment moved to Friday"),Requirement(key="fee",description="No additional charge")])
CONSENT=ConsentLedger(approved=True,revoked=False,recipient="Clinic",purpose="Reschedule",allowed_data=["name"],forbidden_actions=["share payment details","accept paid alternative"],hard_constraints=["No additional charge"])

def test_explicit_payment_action_is_blocked_and_contradicts_fee_requirement():
    a=audit_provider_result(provider={"summary":"Appointment moved; payment was made and the fee was accepted.","evidence":[]},contract=CONTRACT,consent=CONSENT)
    assert a.blocked is True
    assert any(x.requirement_key=="fee" and x.classification==EvidenceClass.CONTRADICTING for x in a.evidence)

def test_requirement_for_new_payment_authority_is_boundary_hit():
    a=audit_provider_result(provider={"summary":"Clinic says it cannot proceed without payment details.","evidence":[]},contract=CONTRACT,consent=CONSENT)
    assert a.blocked is True
    assert "outside the approved consent envelope" in a.reasons[0]

def test_merely_mentioning_payment_is_not_enough_to_claim_violation():
    a=audit_provider_result(provider={"summary":"We discussed the payment policy; no action was taken.","evidence":[]},contract=CONTRACT,consent=CONSENT)
    assert a.blocked is False
    assert a.evidence==[]
