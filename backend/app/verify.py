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
    """Verify the user goal from explicit evidence, never from provider completion alone.

    Evidence is evaluated before transport state. This preserves useful evidence from
    interrupted calls while keeping the fail-closed rule: an incomplete transport can
    never produce VERIFIED_SUCCESS.
    """
    required = [r.key for r in contract.success_conditions if r.required]
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
        # Refutation wins over support until a future chronology-aware resolver proves
        # that a contradiction was explicitly retracted.
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

    # Transport completion is required to promote the goal to VERIFIED_SUCCESS, but
    # evidence collected before an interruption is not discarded.
    if not call_completed:
        if verified:
            return VerificationResult(
                state=GoalState.PARTIAL,
                verified=verified,
                missing=missing,
                contradicted=[],
                refutation_notes=["transport incomplete", *refutation_notes],
                reason="The call did not complete. Explicit evidence was preserved, but goal success cannot be fully established."
            )
        return VerificationResult(
            state=GoalState.UNKNOWN,
            verified=[],
            missing=missing or required,
            contradicted=[],
            refutation_notes=["transport incomplete", *refutation_notes],
            reason="The call did not complete and no required condition has explicit supporting evidence."
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