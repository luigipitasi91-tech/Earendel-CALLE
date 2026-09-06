"""
LLM-assisted Goal Contract extraction (Claude Sonnet 4.6 via Emergent Universal Key).

Falls back to a deterministic extractor when the model is unavailable or output
is not valid JSON. Verify Engine remains fully deterministic regardless.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any

from emergentintegrations.llm.chat import LlmChat, UserMessage


SYSTEM_PROMPT = """You are the Goal Contract compiler for Future Call AI.

Convert the user's natural-language phone task into a strict Goal Contract JSON.
Never invent facts. If a field is not stated by the user, leave it empty.

Return ONLY JSON with this exact shape:

{
  "goal": "<one short sentence>",
  "preferred_outcome": "<one short sentence, may be empty>",
  "hard_constraints": ["<constraint>", "..."],
  "permitted_data": ["<datum the AI may share, e.g. 'Name', 'Booking reference'>"],
  "forbidden_data": ["<datum the AI must never share, e.g. 'Payment details'>"],
  "forbidden_actions": ["<action the AI must not take without new consent>"],
  "success_conditions": [
    {"id": "A", "text": "<explicit condition>", "kind": "affirmative", "keywords": ["..."]},
    {"id": "B", "text": "<explicit condition>", "kind": "no_charge", "keywords": []}
  ]
}

Rules for success_conditions:
- Each condition MUST be independently verifiable from the recipient's speech.
- Use kind="no_charge" for any "no additional charge / no fee" constraint.
- Use kind="affirmative" otherwise, with 1-3 keywords that must appear in the recipient's confirmation.
- Every hard_constraint that is a required outcome should also appear as a success_condition.
"""


def _empty_contract() -> dict:
    return {
        "goal": "",
        "preferred_outcome": "",
        "hard_constraints": [],
        "permitted_data": [],
        "forbidden_data": [],
        "forbidden_actions": [],
        "success_conditions": [],
    }


def _deterministic_extract(request_text: str) -> dict:
    """Fallback extractor for the built-in demo request and simple cases."""
    text = request_text.lower()
    contract = _empty_contract()

    if "appointment" in text and ("move" in text or "reschedule" in text):
        # Try to pick up day of week
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        target_day = next((d for d in days if d in text), "")
        part = "afternoon" if "afternoon" in text else "morning" if "morning" in text else "evening" if "evening" in text else ""
        preferred = " ".join(x for x in [target_day.capitalize(), part] if x).strip()

        contract["goal"] = "Reschedule appointment."
        contract["preferred_outcome"] = preferred or "As soon as possible."
        contract["permitted_data"] = ["Name", "Booking reference"]
        contract["forbidden_data"] = ["Payment details"]
        contract["forbidden_actions"] = ["Accept any paid alternative without new user consent."]

        no_charge = bool(re.search(r"no (additional|extra) (charge|fee|cost)|without (a )?charge", text))
        if no_charge:
            contract["hard_constraints"] = ["No additional charge."]

        conditions = []
        cond_a_text = "The recipient explicitly confirms that the appointment has been moved" + (
            f" to {preferred}." if preferred else "."
        )
        kw = []
        if target_day:
            kw.append(target_day)
        if part:
            kw.append(part)
        if not kw:
            kw = ["rescheduled"]
        conditions.append({"id": "A", "text": cond_a_text, "kind": "affirmative", "keywords": kw})
        if no_charge:
            conditions.append({
                "id": "B",
                "text": "The recipient explicitly confirms that there is no additional charge.",
                "kind": "no_charge",
                "keywords": [],
            })
        contract["success_conditions"] = conditions
        return contract

    # Very generic fallback: single condition around a keyword
    contract["goal"] = request_text.strip().rstrip(".") + "." if request_text.strip() else ""
    contract["permitted_data"] = ["Name"]
    contract["forbidden_data"] = ["Payment details"]
    contract["forbidden_actions"] = ["Agree to any paid change without new user consent."]
    contract["success_conditions"] = [{
        "id": "A",
        "text": "The recipient explicitly confirms the requested outcome.",
        "kind": "affirmative",
        "keywords": ["confirmed"],
    }]
    return contract


def _coerce_contract(raw: dict) -> dict:
    base = _empty_contract()
    for k in base:
        if k in raw and raw[k] is not None:
            base[k] = raw[k]
    # ensure ids on success_conditions
    seen = set()
    letters = "ABCDEFGHIJKLMNOP"
    fixed = []
    for i, c in enumerate(base["success_conditions"] or []):
        if not isinstance(c, dict):
            continue
        cid = c.get("id") or letters[i] if i < len(letters) else str(i)
        if cid in seen:
            cid = f"{cid}{i}"
        seen.add(cid)
        fixed.append({
            "id": cid,
            "text": (c.get("text") or "").strip(),
            "kind": c.get("kind") if c.get("kind") in ("affirmative", "no_charge", "custom") else "affirmative",
            "keywords": [k for k in (c.get("keywords") or []) if isinstance(k, str)],
        })
    base["success_conditions"] = fixed
    return base


async def extract_contract(request_text: str) -> dict:
    """
    Extract a Goal Contract from natural language. Uses Claude Sonnet 4.6 if
    the Emergent LLM key is set, otherwise falls back to deterministic.
    """
    api_key = (os.environ.get("EMERGENT_LLM_KEY") or "").strip()
    if not api_key:
        return _deterministic_extract(request_text)

    try:
        chat = LlmChat(
            api_key=api_key,
            session_id=f"contract-{uuid.uuid4()}",
            system_message=SYSTEM_PROMPT,
        ).with_model("anthropic", "claude-sonnet-4-6")

        resp = await chat.send_message(UserMessage(text=request_text))
        text = resp if isinstance(resp, str) else str(resp)
        # extract JSON block
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return _deterministic_extract(request_text)
        parsed = json.loads(m.group(0))
        contract = _coerce_contract(parsed)
        if not contract["success_conditions"]:
            # LLM returned no conditions — safer to fall back so verifier has something to check
            fallback = _deterministic_extract(request_text)
            contract["success_conditions"] = fallback["success_conditions"]
        return contract
    except Exception:
        return _deterministic_extract(request_text)
