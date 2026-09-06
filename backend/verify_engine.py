"""
Deterministic Verify Engine for Future Call AI.

Core principle: Provider state != Goal state. AI claims != Evidence.
Only explicit supporting evidence from the recipient/human side of the
transcript can promote a condition to CONFIRMED. Explicit contradiction
downgrades to CONTRADICTED. Everything else is UNVERIFIED.
"""
from __future__ import annotations

from typing import Any
import re

# Goal states
VERIFIED_SUCCESS = "VERIFIED_SUCCESS"
PARTIAL = "PARTIAL"
UNKNOWN = "UNKNOWN"
FAILED = "FAILED"

# Per-condition states
CONFIRMED = "CONFIRMED"
CONTRADICTED = "CONTRADICTED"
UNVERIFIED = "UNVERIFIED"


AFFIRM_PATTERNS = [
    r"\byes\b", r"\bconfirmed\b", r"\bthat's confirmed\b", r"\bdone\b",
    r"\bmoved\b", r"\brescheduled\b", r"\bbooked\b", r"\ball set\b",
    r"\bno charge\b", r"\bno additional charge\b", r"\bno extra charge\b",
    r"\bno fee\b", r"\bfree of charge\b", r"\bat no cost\b",
    r"\bwithout any charge\b", r"\bcomplimentary\b",
]

DENY_PATTERNS = [
    r"\bno\b", r"\bcannot\b", r"\bcan't\b", r"\bunable\b", r"\bnot able\b",
    r"\bunavailable\b", r"\bwe don't\b", r"\bwe do not\b", r"\bimpossible\b",
    r"\brefuse\b", r"\bdeclined\b",
]

CHARGE_PRESENT_PATTERNS = [
    r"\$\s?\d+", r"\bfee of\b", r"\bcharge of\b", r"\bthere (is|will be) (a|an) (charge|fee|cost|surcharge)\b",
    r"\bpay\s+(a|an|another|extra|additional)\b", r"\bsurcharge\b",
    r"\brescheduling fee\b", r"\bchange fee\b", r"\bpayable\b",
]

VOICEMAIL_MARKERS = [
    "voicemail", "leave a message", "after the tone", "at the beep",
    "not available to take your call", "please record",
]


def _has(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _find_evidence(text: str, patterns: list[str]) -> str | None:
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


def evaluate_condition(condition: dict, transcript: list[dict]) -> dict:
    """
    Evaluate a single success condition against recipient turns.

    condition = {
        "id": str,
        "text": str,           # human-readable requirement
        "kind": "affirmative" | "no_charge" | "custom",
        "keywords": [str],     # optional custom keywords requiring recipient affirmation
    }
    """
    kind = condition.get("kind", "custom")
    keywords = [k.lower() for k in condition.get("keywords", [])]

    matched_evidence: list[dict] = []
    contradicting_evidence: list[dict] = []

    for turn in transcript:
        # Only recipient/human speech counts as external evidence.
        if turn.get("role") not in ("recipient", "human"):
            continue
        text = (turn.get("text") or "").strip()
        if not text:
            continue
        low = text.lower()

        if kind == "no_charge":
            # Positive: explicit no-charge affirmation.
            ev = _find_evidence(low, [
                r"\bno additional charge\b", r"\bno extra charge\b",
                r"\bno charge\b", r"\bno fee\b", r"\bfree of charge\b",
                r"\bcomplimentary\b", r"\bat no cost\b",
                r"\bwithout (any|an additional) (charge|fee)\b",
            ])
            if ev:
                matched_evidence.append({"turn": turn, "match": ev})
            # Negative: any indication of a charge.
            neg = _find_evidence(low, CHARGE_PRESENT_PATTERNS)
            if neg:
                contradicting_evidence.append({"turn": turn, "match": neg})

        elif kind == "affirmative":
            # Positive: keyword present AND affirmation nearby.
            keyword_hit = next((k for k in keywords if k in low), None)
            if keyword_hit and _has(low, AFFIRM_PATTERNS):
                matched_evidence.append(
                    {"turn": turn, "match": keyword_hit}
                )
            # Negative: keyword present + denial.
            if keyword_hit and _has(low, DENY_PATTERNS) and not _has(low, AFFIRM_PATTERNS):
                contradicting_evidence.append(
                    {"turn": turn, "match": keyword_hit}
                )

        else:  # custom
            if all(k in low for k in keywords) and _has(low, AFFIRM_PATTERNS):
                matched_evidence.append({"turn": turn, "match": ", ".join(keywords)})
            if all(k in low for k in keywords) and _has(low, DENY_PATTERNS) and not _has(low, AFFIRM_PATTERNS):
                contradicting_evidence.append({"turn": turn, "match": ", ".join(keywords)})

    # Contradiction takes precedence.
    if contradicting_evidence:
        state = CONTRADICTED
    elif matched_evidence:
        state = CONFIRMED
    else:
        state = UNVERIFIED

    return {
        "condition_id": condition["id"],
        "requirement": condition["text"],
        "state": state,
        "supporting_evidence": matched_evidence,
        "contradicting_evidence": contradicting_evidence,
    }


def is_voicemail(transcript: list[dict]) -> bool:
    """Detect if the call was answered by voicemail/IVR (no human evidence)."""
    text_blob = " ".join(
        (t.get("text") or "").lower()
        for t in transcript
        if t.get("role") in ("recipient", "system_event", "human")
    )
    return any(m in text_blob for m in VOICEMAIL_MARKERS)


def verify(
    contract: dict,
    transcript: list[dict],
    provider_state: str,
    consent_revoked: bool = False,
    provider_failed: bool = False,
    websocket_failed: bool = False,
) -> dict:
    """
    Determine overall goal verdict from transcript and telephony signals.

    Returns dict with verdict, per_condition results, and reason.
    """
    conditions = contract.get("success_conditions", []) or []
    per_condition = [evaluate_condition(c, transcript) for c in conditions]

    confirmed = [r for r in per_condition if r["state"] == CONFIRMED]
    contradicted = [r for r in per_condition if r["state"] == CONTRADICTED]
    unverified = [r for r in per_condition if r["state"] == UNVERIFIED]

    # Hard failure modes: never promote to VERIFIED SUCCESS.
    if consent_revoked:
        verdict = FAILED
        reason = "User consent was revoked before all conditions were confirmed."
    elif contradicted:
        verdict = FAILED
        reason = "At least one required condition was explicitly contradicted by the recipient."
    elif provider_failed and not confirmed:
        verdict = FAILED
        reason = "Telephony provider reported a failure and no goal condition was confirmed."
    elif websocket_failed and not confirmed:
        verdict = UNKNOWN
        reason = "Voice session (ConversationRelay) disconnected before any evidence was collected."
    elif is_voicemail(transcript) and not confirmed:
        verdict = UNKNOWN
        reason = "Call appears to have reached voicemail/IVR. No human confirmation captured."
    elif not conditions:
        verdict = UNKNOWN
        reason = "Goal contract has no explicit success conditions to verify."
    elif len(confirmed) == len(conditions):
        verdict = VERIFIED_SUCCESS
        reason = "Every required success condition has explicit supporting evidence."
    elif confirmed and unverified:
        verdict = PARTIAL
        reason = f"{len(confirmed)}/{len(conditions)} required conditions confirmed. Remaining conditions lack explicit evidence."
    else:
        verdict = UNKNOWN
        reason = "Call ended without explicit evidence for the required conditions."

    return {
        "verdict": verdict,
        "reason": reason,
        "per_condition": per_condition,
        "provider_state": provider_state,
        "telephony_completed": provider_state == "completed",
    }


def recipient_wants_forbidden(
    utterance: str, forbidden_actions: list[str], forbidden_data: list[str]
) -> str | None:
    """
    If a recipient utterance attempts to elicit a forbidden action or data,
    return the matched forbidden item. Guardian must BLOCK — never silently comply.
    """
    low = utterance.lower()
    for item in list(forbidden_actions or []) + list(forbidden_data or []):
        it = item.lower().strip()
        if not it:
            continue
        # heuristic: forbidden keyword present
        # e.g. "payment details" -> "card", "credit card", "cvv"
        tokens = [t for t in re.split(r"\W+", it) if t]
        if tokens and all(t in low for t in tokens):
            return item
    # extra heuristic: recipient asking for payment/card details
    if re.search(r"\b(credit card|card number|cvv|expiry|expiration|billing details|payment details)\b", low):
        return "payment details"
    return None
