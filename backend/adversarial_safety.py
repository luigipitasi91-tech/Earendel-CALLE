"""Offline adversarial verification model. No CALL-E SDK, network or credits.

This module is intentionally independent of production call execution until
the existing backend's actual contracts are mapped and regression-tested.
"""
from dataclasses import dataclass
from enum import Enum


class Verdict(str, Enum):
    VERIFIED_SUCCESS = "VERIFIED_SUCCESS"
    NEEDS_HUMAN = "NEEDS_HUMAN"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class Evidence:
    source: str
    call_id: str
    recipient: str
    condition: str
    stance: str
    authenticated: bool = False


def adjudicate(required_conditions, evidence, *, call_id, recipient):
    """Contradictions survive supporting evidence; provider completion is not finality."""
    findings = {}
    for condition in required_conditions:
        items = [e for e in evidence if e.condition == condition]
        mismatched = [e for e in items if e.call_id != call_id or e.recipient != recipient]
        trusted = [e for e in items if e.authenticated and e.call_id == call_id and e.recipient == recipient]
        if mismatched:
            findings[condition] = "SOURCE_BINDING_MISMATCH"
        elif any(e.stance == "CONTRADICTING" for e in trusted):
            findings[condition] = "CONTRADICTED"
        elif any(e.stance == "SUPPORTING" for e in trusted):
            findings[condition] = "SUPPORTED"
        else:
            findings[condition] = "INSUFFICIENT"
    if any(v in ("CONTRADICTED", "SOURCE_BINDING_MISMATCH") for v in findings.values()):
        verdict = Verdict.NEEDS_HUMAN
    elif all(v == "SUPPORTED" for v in findings.values()) and findings:
        verdict = Verdict.VERIFIED_SUCCESS
    else:
        verdict = Verdict.UNKNOWN
    return {"verdict": verdict.value, "findings": findings}


def retry_decision(*, idempotency_key, persisted_job, provider_state, lookup_confirmed):
    """Fail closed for uncertain execution; do not initiate a second chargeable call."""
    if not idempotency_key:
        return "BLOCK_MISSING_IDEMPOTENCY_KEY"
    if persisted_job:
        return "RESUME_EXISTING_JOB"
    if not lookup_confirmed:
        return "BLOCK_UNKNOWN_PROVIDER_STATE"
    if provider_state in ("pending", "ringing", "active", "completed", "unknown", "timeout"):
        return "BLOCK_POSSIBLE_DUPLICATE"
    return "REQUIRES_EXPLICIT_NEW_AUTHORIZATION"
