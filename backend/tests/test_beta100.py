import pytest
from app.models import GoalContract, Requirement, EvidenceItem, EvidenceClass, GoalState
from app.verify import verify_goal

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

def e(key, cls):
    return EvidenceItem(requirement_key=key, text=f"{key}:{cls}", classification=cls, explicit=True)

cases = []
for i in range(25):
    cases.append(("verified", [e("date", EvidenceClass.SUPPORTING), e("fee", EvidenceClass.SUPPORTING)], True, GoalState.VERIFIED_SUCCESS))
for i in range(20):
    cases.append(("partial", [e("date", EvidenceClass.SUPPORTING)], True, GoalState.PARTIAL))
for i in range(20):
    cases.append(("unknown", [], True, GoalState.UNKNOWN))
for i in range(15):
    cases.append(("failed", [e("date", EvidenceClass.SUPPORTING), e("fee", EvidenceClass.CONTRADICTING)], True, GoalState.FAILED))
for i in range(10):
    cases.append(("neutral", [e("date", EvidenceClass.NEUTRAL_OR_INSUFFICIENT), e("fee", EvidenceClass.NEUTRAL_OR_INSUFFICIENT)], True, GoalState.UNKNOWN))
# Interrupted transport preserves explicit evidence but can never promote to VERIFIED_SUCCESS.
# With all conditions explicitly supported, the safe state is PARTIAL until transport completion is established.
for i in range(10):
    cases.append(("dropped", [e("date", EvidenceClass.SUPPORTING), e("fee", EvidenceClass.SUPPORTING)], False, GoalState.PARTIAL))

assert len(cases) == 100

@pytest.mark.parametrize("name,evidence,completed,expected", cases)
def test_beta_100(name, evidence, completed, expected):
    assert verify_goal(contract(), evidence, completed).state == expected
