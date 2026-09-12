from dataclasses import dataclass
from .models import EvidenceClass, EvidenceItem


@dataclass
class RuntimeGuardianAudit:
    blocked: bool
    reasons: list[str]
    evidence: list[EvidenceItem]


def audit_provider_result(*, provider: dict, contract, consent) -> RuntimeGuardianAudit:
    """Audit terminal provider text for explicit signs that the call crossed or hit a consent boundary.

    This is deliberately conservative: it does not infer that an action occurred merely because a
    sensitive concept was mentioned. It only flags explicit provider evidence indicating disclosure,
    acceptance, payment, or a requirement to cross the boundary.
    """
    chunks = [provider.get("summary") or ""] + [str(x) for x in (provider.get("evidence") or [])]
    text = " | ".join(chunks).lower()
    reasons = []

    explicit_payment = [
        "payment details were provided", "card details were provided", "card number was provided",
        "payment was made", "paid the fee", "accepted the fee", "agreed to the fee",
        "accepted the paid alternative",
    ]
    requires_escalation = [
        "requires payment details", "required payment details", "requires a payment",
        "cannot proceed without payment", "needs card details", "requires additional consent",
    ]

    forbidden = " ".join(consent.forbidden_actions).lower()
    if ("payment" in forbidden or "card" in forbidden or "paid alternative" in forbidden) and any(p in text for p in explicit_payment):
        reasons.append("Provider evidence indicates a forbidden payment/data action occurred")
    if any(p in text for p in requires_escalation):
        reasons.append("Completion requires authority outside the approved consent envelope")

    evidence = []
    if reasons:
        # A runtime boundary hit is evidence against requirements whose completion depends on
        # respecting hard constraints. The verifier still independently evaluates goal evidence.
        for req in contract.success_conditions:
            desc = req.description.lower()
            if any(term in desc for term in ["fee", "charge", "payment", "without paying", "free"]):
                evidence.append(EvidenceItem(
                    requirement_key=req.key,
                    text="; ".join(reasons),
                    source="Earendel Runtime Guardian",
                    classification=EvidenceClass.CONTRADICTING,
                    explicit=True,
                ))
    return RuntimeGuardianAudit(blocked=bool(reasons), reasons=reasons, evidence=evidence)
