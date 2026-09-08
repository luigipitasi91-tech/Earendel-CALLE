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

# Strict, explicit contradiction constructs. A recipient turn only counts as
# a CONTRADICTION when one of these patterns is present in the SAME utterance
# as the keyword. A bare "no" (e.g. "no problem") is NOT a contradiction.
STRONG_DENY_PATTERNS = [
    r"\bcannot\b", r"\bcan(?:'|no)t\b", r"\bcan not\b",
    r"\bunable\b", r"\bnot able\b",
    r"\bunavailable\b", r"\bnot available\b",
    r"\bwon't\b", r"\bwill not\b",
    r"\bimpossible\b", r"\brefuse[ds]?\b", r"\bdeclined?\b",
    r"\bwe (don't|do not) (do|allow|offer|have)\b",
    r"\bnot\s+(?:be|been|going to be|going)\s+(?:moved|rescheduled|changed|available)\b",
    r"\bnot\s+(?:possible|going to (?:happen|work))\b",
    r"\b(?:remains|stays|staying|stays put)\b\s+(?:on|at|as|the same)\b",
    r"\boriginal (?:slot|appointment|booking)\s+(?:stays|remains)\b",
    r"\bstays as is\b",
    r"\bkeep(?:ing)?\s+(?:the|your)\s+(?:current|existing)\s+(?:slot|appointment|booking)\b",
]

# Direct negation of a specific keyword: "not friday", "no friday", "never friday".
def _keyword_negated(low: str, keyword: str) -> bool:
    kw = re.escape(keyword)
    return bool(re.search(rf"\b(?:not|no|never)\s+(?:on\s+|at\s+|going\s+to\s+be\s+)?{kw}\b", low))

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
            keyword_hit = next((k for k in keywords if k in low), None)

            # SUPPORTING: keyword present AND explicit affirmation nearby.
            if keyword_hit and _has(low, AFFIRM_PATTERNS):
                matched_evidence.append({"turn": turn, "match": keyword_hit})
                continue  # a single utterance is not both supporting and contradicting

            # For movement-type requirements ("moved to ...", "rescheduled to ..."),
            # an explicit "stays on / remains on / original slot stays" utterance
            # contradicts the condition even without the target-day keyword.
            requirement_low = (condition.get("text") or "").lower()
            is_move_requirement = any(
                w in requirement_low for w in ("moved", "reschedul", "changed")
            )
            anti_move = _find_evidence(low, [
                r"\b(?:stays|remains|staying|remaining)\s+(?:on|at|as|the same)\b",
                r"\boriginal (?:slot|appointment|booking)\s+(?:stays|remains)\b",
                r"\bstays as is\b",
                r"\bkeep(?:ing)?\s+(?:the|your)\s+(?:current|existing|original)\s+(?:slot|appointment|booking|time)\b",
            ])
            if is_move_requirement and anti_move:
                contradicting_evidence.append({"turn": turn, "match": anti_move})
                continue

            # CONTRADICTING: only when there is an EXPLICIT denial construct in
            # the same utterance as the keyword, OR when the keyword itself is
            # directly negated. Bare "no" (e.g. "no problem") does NOT qualify.
            if keyword_hit and (
                _has(low, STRONG_DENY_PATTERNS) or _keyword_negated(low, keyword_hit)
            ):
                contradicting_evidence.append({"turn": turn, "match": keyword_hit})
            # else: NEUTRAL / INSUFFICIENT — record nothing.

        else:  # custom
            if not keywords:
                continue
            all_present = all(k in low for k in keywords)
            if all_present and _has(low, AFFIRM_PATTERNS):
                matched_evidence.append({"turn": turn, "match": ", ".join(keywords)})
                continue
            if all_present and _has(low, STRONG_DENY_PATTERNS):
                contradicting_evidence.append({"turn": turn, "match": ", ".join(keywords)})
            # else: NEUTRAL / INSUFFICIENT.

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
