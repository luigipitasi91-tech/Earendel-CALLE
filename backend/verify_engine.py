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

# Per-condition classification (evidence-first).
SUPPORTING = "SUPPORTING"
CONTRADICTING = "CONTRADICTING"
NEUTRAL_OR_INSUFFICIENT = "NEUTRAL_OR_INSUFFICIENT"

# Backwards-compat aliases (old names used by earlier tests / callers).
CONFIRMED = SUPPORTING
CONTRADICTED = CONTRADICTING
UNVERIFIED = NEUTRAL_OR_INSUFFICIENT


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
        state = CONTRADICTING
    elif matched_evidence:
        state = SUPPORTING
    else:
        state = NEUTRAL_OR_INSUFFICIENT

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


def attempt_refutation(
    *,
    contract: dict,
    transcript: list[dict],
    per_condition: list[dict],
    provider_state: str,
    consent_revoked: bool,
    provider_failed: bool,
    websocket_failed: bool,
    guardian_blocks: list[dict] | None = None,
) -> list[dict]:
    """
    Refutation-first pass. Try to falsify VERIFIED_SUCCESS. Returns a list of
    checks; each has {check, passed, detail}. `passed=True` means the check
    could NOT falsify success. If any `passed=False`, VERIFIED_SUCCESS must be
    withheld.
    """
    guardian_blocks = guardian_blocks or []
    checks: list[dict] = []

    # 1. Any hard-constraint contradiction?
    contradicted = [r for r in per_condition if r["state"] == CONTRADICTING]
    checks.append({
        "check": "no_condition_contradicted",
        "passed": not contradicted,
        "detail": (
            f"{len(contradicted)} condition(s) explicitly contradicted by recipient."
            if contradicted else "No explicit contradiction detected."
        ),
    })

    # 2. Any unsupported (NEUTRAL_OR_INSUFFICIENT) condition?
    unsupported = [r for r in per_condition if r["state"] == NEUTRAL_OR_INSUFFICIENT]
    checks.append({
        "check": "all_conditions_supported",
        "passed": not unsupported and bool(per_condition),
        "detail": (
            f"{len(unsupported)} condition(s) lack explicit supporting evidence."
            if unsupported else "All conditions have explicit supporting evidence."
        ) if per_condition else "Contract has no success conditions.",
    })

    # 3. Evidence must be recipient/system, never agent-only.
    agent_only = any(
        any(e["turn"].get("role") == "agent" for e in r.get("supporting_evidence", []))
        for r in per_condition
    )
    checks.append({
        "check": "evidence_not_agent_only",
        "passed": not agent_only,
        "detail": "Supporting evidence found on agent turns — invalid." if agent_only else "All supporting evidence comes from recipient/system.",
    })

    # 4. Guardian block that materially prevents completion.
    material_block = bool(guardian_blocks) and bool(unsupported)
    checks.append({
        "check": "no_material_guardian_block",
        "passed": not material_block,
        "detail": (
            "Guardian blocked an item AND at least one success condition remains unsupported."
            if material_block else
            f"Guardian blocks: {len(guardian_blocks)}. None prevented required evidence."
        ),
    })

    # 5. Provider-vs-task confusion: provider completed but no supporting evidence.
    provider_confusion = (
        provider_state == "completed" and not any(r["state"] == SUPPORTING for r in per_condition)
    )
    checks.append({
        "check": "provider_completion_not_task_completion",
        "passed": not provider_confusion,
        "detail": (
            "Provider reported 'completed' but no success condition has supporting evidence."
            if provider_confusion else "Provider state and task evidence are consistent."
        ),
    })

    # 6. Consent must still be active.
    checks.append({
        "check": "consent_still_active",
        "passed": not consent_revoked,
        "detail": "User consent revoked." if consent_revoked else "Consent active.",
    })

    # 7. Transport failure must not silently pass as success.
    checks.append({
        "check": "no_transport_failure",
        "passed": not (provider_failed or websocket_failed),
        "detail": (
            f"Transport issues: provider_failed={provider_failed}, websocket_failed={websocket_failed}."
            if (provider_failed or websocket_failed) else "No transport failure detected."
        ),
    })

    return checks


def verify(
    contract: dict,
    transcript: list[dict],
    provider_state: str,
    consent_revoked: bool = False,
    provider_failed: bool = False,
    websocket_failed: bool = False,
    guardian_blocks: list[dict] | None = None,
) -> dict:
    """
    Determine overall goal verdict.

    Runs evidence classification, then a refutation-first pass. VERIFIED_SUCCESS
    is only returned if every refutation check passes.
    """
    conditions = contract.get("success_conditions", []) or []
    per_condition = [evaluate_condition(c, transcript) for c in conditions]

    supporting = [r for r in per_condition if r["state"] == SUPPORTING]
    contradicting = [r for r in per_condition if r["state"] == CONTRADICTING]
    neutral = [r for r in per_condition if r["state"] == NEUTRAL_OR_INSUFFICIENT]

    refutations = attempt_refutation(
        contract=contract,
        transcript=transcript,
        per_condition=per_condition,
        provider_state=provider_state,
        consent_revoked=consent_revoked,
        provider_failed=provider_failed,
        websocket_failed=websocket_failed,
        guardian_blocks=guardian_blocks,
    )
    failed_checks = [c for c in refutations if not c["passed"]]

    # Terminal decision — never bypass refutations for VERIFIED_SUCCESS.
    if consent_revoked:
        verdict, reason = FAILED, "User consent was revoked before all conditions were confirmed."
    elif contradicting:
        verdict, reason = FAILED, "At least one required condition was explicitly contradicted by the recipient."
    elif provider_failed and not supporting:
        verdict, reason = FAILED, "Telephony provider reported a failure and no goal condition was supported."
    elif websocket_failed and not supporting:
        verdict, reason = UNKNOWN, "Voice session disconnected before any evidence was collected."
    elif is_voicemail(transcript) and not supporting:
        verdict, reason = UNKNOWN, "Call appears to have reached voicemail/IVR. No human confirmation captured."
    elif not conditions:
        verdict, reason = UNKNOWN, "Goal contract has no explicit success conditions to verify."
    elif len(supporting) == len(conditions) and not failed_checks:
        verdict, reason = VERIFIED_SUCCESS, "Every required success condition has explicit supporting evidence and all refutation checks passed."
    elif len(supporting) == len(conditions) and failed_checks:
        # All conditions supported, but a refutation still fires — must NOT be VERIFIED_SUCCESS.
        verdict = PARTIAL
        reason = "All conditions appear supported, but refutation failed: " + "; ".join(c["detail"] for c in failed_checks)
    elif supporting and neutral:
        verdict = PARTIAL
        reason = f"{len(supporting)}/{len(conditions)} required conditions supported. Remaining conditions lack explicit evidence."
    else:
        verdict, reason = UNKNOWN, "Call ended without explicit evidence for the required conditions."

    return {
        "verdict": verdict,
        "reason": reason,
        "per_condition": per_condition,
        "refutations": refutations,
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


def pre_execution_check(contract: dict, *, mode: str, recipient_number: str = "") -> dict:
    """
    Enumerate KNOWN RISKS and UNKNOWNS before execution. Unknown information
    is represented explicitly and never invented.
    """
    known_risks: list[str] = []
    unknowns: list[str] = []

    if not contract.get("success_conditions"):
        known_risks.append("No explicit success conditions — verification cannot promote to VERIFIED_SUCCESS.")
    if not contract.get("hard_constraints"):
        unknowns.append("hard_constraints: none stated by the user.")
    if not contract.get("forbidden_data"):
        unknowns.append("forbidden_data: none stated by the user.")
    if not contract.get("permitted_data"):
        unknowns.append("permitted_data: none stated — agent will not proactively share user data.")
    if not contract.get("preferred_outcome"):
        unknowns.append("preferred_outcome: not stated.")

    if mode.upper() == "REAL" and not recipient_number and not contract.get("recipient_number"):
        known_risks.append("REAL mode requested but recipient_number is missing.")

    if mode.upper() == "SIMULATED":
        known_risks.append("Execution is SIMULATED — no real telephony evidence will be produced.")

    return {
        "mode": mode.upper(),
        "known_risks": known_risks,
        "unknowns": unknowns,
        "contract_snapshot": {
            "goal": contract.get("goal") or "",
            "preferred_outcome": contract.get("preferred_outcome") or "",
            "hard_constraints": contract.get("hard_constraints") or [],
            "permitted_data": contract.get("permitted_data") or [],
            "forbidden_data": contract.get("forbidden_data") or [],
            "forbidden_actions": contract.get("forbidden_actions") or [],
            "success_conditions": contract.get("success_conditions") or [],
        },
    }
