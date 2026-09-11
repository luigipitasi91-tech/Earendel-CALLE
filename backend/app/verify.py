from collections import defaultdict
from .models import GoalContract, EvidenceItem, VerificationResult, GoalState, EvidenceClass


def attempt_refutation(contract: GoalContract, evidence: list[EvidenceItem]) -> list[str]:
    notes = []
    for req in contract.success_conditions:
        items = [e for e in evidence if e.requirement_key == req.key]
        if any(e.explicit and e.classification == EvidenceClass.CONTRADICTING for e in items):
            notes.append(f"{req.key}: explicit contradiction found")
        elif req.required and not any(e.explicit and e.classification == EvidenceClass.SUPPORTING for e in items):
            notes.append(f"{req.key}: required support missing")
    return notes


def verify_goal(contract: GoalContract, evidence: list[EvidenceItem], call_completed: bool) -> VerificationResult:
    required = [r.key for r in contract.success_conditions if r.required]
    if not call_completed:
        return VerificationResult(
            state=GoalState.UNKNOWN,
            verified=[],
            missing=required,
            contradicted=[],
            refutation_notes=["transport incomplete"],
            reason="The call did not complete; goal success cannot be established."
        )

    by_key = defaultdict(list)
    for item in evidence:
        by_key[item.requirement_key].append(item)

    verified, missing, contradicted = [], [], []

    for req in contract.success_conditions:
        items = by_key.get(req.key, [])
        has_contradiction = any(
            i.explicit and i.classification == EvidenceClass.CONTRADICTING for i in items
        )
        has_support = any(
            i.explicit and i.classification == EvidenceClass.SUPPORTING for i in items
        )
        if has_contradiction:
            contradicted.append(req.key)
        elif has_support:
            verified.append(req.key)
        elif req.required:
            missing.append(req.key)

    refutation_notes = attempt_refutation(contract, evidence)

    if contradicted:
        return VerificationResult(
            state=GoalState.FAILED,
            verified=verified,
            missing=missing,
            contradicted=contradicted,
            refutation_notes=refutation_notes,
            reason="At least one required success condition is explicitly contradicted."
        )

    if required and not missing and set(required).issubset(set(verified)):
        return VerificationResult(
            state=GoalState.VERIFIED_SUCCESS,
            verified=verified,
            missing=[],
            contradicted=[],
            refutation_notes=[],
            reason="Every required condition has explicit supporting evidence and no unresolved contradiction."
        )

    if verified:
        return VerificationResult(
            state=GoalState.PARTIAL,
            verified=verified,
            missing=missing,
            contradicted=[],
            refutation_notes=refutation_notes,
            reason="Some required conditions are supported, but at least one remains unverified."
        )

    return VerificationResult(
        state=GoalState.UNKNOWN,
        verified=[],
        missing=missing or required,
        contradicted=[],
        refutation_notes=refutation_notes,
        reason="Insufficient explicit evidence."
    )
