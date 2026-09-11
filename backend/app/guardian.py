from .models import GoalContract, ConsentLedger


class GuardianDecision:
    def __init__(self, allowed: bool, reason: str):
        self.allowed = allowed
        self.reason = reason


def evaluate_before_call(contract: GoalContract, consent: ConsentLedger) -> GuardianDecision:
    if not consent.approved:
        return GuardianDecision(False, "Explicit consent missing.")
    if consent.revoked:
        return GuardianDecision(False, "Consent has been revoked.")
    if not consent.recipient.strip():
        return GuardianDecision(False, "Recipient missing.")
    if not consent.purpose.strip():
        return GuardianDecision(False, "Purpose missing.")

    if not set(consent.allowed_data).issubset(set(contract.allowed_data)):
        return GuardianDecision(False, "Consent permits data outside the Goal Contract.")
    if not set(contract.forbidden_actions).issubset(set(consent.forbidden_actions)):
        return GuardianDecision(False, "Consent weakens a forbidden action.")
    if not set(contract.hard_constraints).issubset(set(consent.hard_constraints)):
        return GuardianDecision(False, "Consent weakens a hard constraint.")
    return GuardianDecision(True, "Guardian approved execution.")


def recipient_request_allowed(requested_action: str, contract: GoalContract) -> GuardianDecision:
    normalized = requested_action.lower().strip()
    for forbidden in contract.forbidden_actions:
        f = forbidden.lower().strip()
        if f and (f in normalized or normalized in f):
            return GuardianDecision(False, f"Recipient request conflicts with forbidden action: {forbidden}")

    for constraint in contract.hard_constraints:
        c = constraint.lower()
        if "no additional charge" in c and any(k in normalized for k in [
            "additional fee", "extra charge", "£", "$", "payment", "card details", "credit card"
        ]):
            return GuardianDecision(False, "Recipient request conflicts with no-additional-charge constraint.")
    return GuardianDecision(True, "No direct conflict detected.")
