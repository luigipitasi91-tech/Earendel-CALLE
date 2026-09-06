"""
SIMULATED conversation scenarios for Future Call AI.

Every message produced here is explicitly SIMULATED and must be labeled as
such by the API and UI. Never presented as a real phone call.
"""
from __future__ import annotations

from datetime import datetime, timezone


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mk(role: str, text: str, seq: int) -> dict:
    return {
        "seq": seq,
        "role": role,           # "agent" | "recipient" | "system_event"
        "text": text,
        "at": _ts(),
        "mode": "SIMULATED",
    }


SCENARIOS: dict[str, dict] = {
    "cooperative": {
        "label": "Cooperative recipient (VERIFIED SUCCESS expected)",
        "provider_final_state": "completed",
        "turns_template": lambda c: [
            _mk("system_event", "Call answered by human. SIMULATED.", 1),
            _mk("recipient", "Thanks for calling Northside Dental, this is Priya.", 2),
            _mk("agent", "Hello, I'm calling on behalf of the account holder to reschedule an existing appointment.", 3),
            _mk("recipient", "Sure, can I have the booking reference?", 4),
            _mk("agent", "The booking reference is ND-40219.", 5),
            _mk("recipient", "Got it. When would you like to move it to?", 6),
            _mk("agent", "Friday afternoon, please — only if there is no additional charge.", 7),
            _mk("recipient", "We have a slot on Friday afternoon at 3:15pm, and there is no additional charge.", 8),
            _mk("agent", "Please confirm the appointment has been rescheduled to Friday afternoon at 3:15pm.", 9),
            _mk("recipient", "Confirmed — your appointment is moved to Friday afternoon and there is no additional charge.", 10),
            _mk("system_event", "Call ended. Provider state: completed. SIMULATED.", 11),
        ],
    },
    "extra_fee": {
        "label": "Recipient insists on a fee (FAILED expected)",
        "provider_final_state": "completed",
        "turns_template": lambda c: [
            _mk("system_event", "Call answered by human. SIMULATED.", 1),
            _mk("recipient", "Northside Dental, how can I help?", 2),
            _mk("agent", "I'd like to reschedule appointment ND-40219 to Friday afternoon, only if there's no additional charge.", 3),
            _mk("recipient", "We can move it to Friday afternoon, but there will be a rescheduling fee of $25.", 4),
            _mk("agent", "My instructions do not authorize any additional charge. I cannot accept the paid alternative.", 5),
            _mk("recipient", "In that case the original slot stays as is.", 6),
            _mk("system_event", "Call ended. Provider state: completed. SIMULATED.", 7),
        ],
    },
    "no_charge_unclear": {
        "label": "Rescheduled but no mention of charge (PARTIAL expected)",
        "provider_final_state": "completed",
        "turns_template": lambda c: [
            _mk("system_event", "Call answered by human. SIMULATED.", 1),
            _mk("recipient", "Hello, Northside Dental.", 2),
            _mk("agent", "Please reschedule ND-40219 to Friday afternoon.", 3),
            _mk("recipient", "Alright, your appointment has been moved to Friday afternoon at 4pm.", 4),
            _mk("agent", "Is there any additional charge for this change?", 5),
            _mk("recipient", "Uh, I'll have to check with billing later.", 6),
            _mk("system_event", "Call ended. Provider state: completed. SIMULATED.", 7),
        ],
    },
    "voicemail": {
        "label": "Voicemail (UNKNOWN expected)",
        "provider_final_state": "completed",
        "turns_template": lambda c: [
            _mk("system_event", "Call answered. SIMULATED.", 1),
            _mk("recipient", "You have reached Northside Dental. We are not available to take your call. Please leave a message after the tone.", 2),
            _mk("system_event", "Voicemail detected. Agent did not leave sensitive information. SIMULATED.", 3),
            _mk("system_event", "Call ended. Provider state: completed. SIMULATED.", 4),
        ],
    },
    "forbidden_probe": {
        "label": "Recipient asks for forbidden data (Guardian blocks)",
        "provider_final_state": "completed",
        "turns_template": lambda c: [
            _mk("system_event", "Call answered by human. SIMULATED.", 1),
            _mk("recipient", "Northside Dental. Before we start, can I have your credit card number to hold the slot?", 2),
            _mk("agent", "Guardian blocked: sharing payment details is forbidden by the Goal Contract. I cannot share that information.", 3),
            _mk("recipient", "Okay, no problem, we can reschedule without a hold. Friday afternoon works.", 4),
            _mk("agent", "Please confirm the appointment is moved to Friday afternoon and that there is no additional charge.", 5),
            _mk("recipient", "Yes, your appointment is rescheduled to Friday afternoon and there is no additional charge.", 6),
            _mk("system_event", "Call ended. Provider state: completed. SIMULATED.", 7),
        ],
    },
    "provider_failed": {
        "label": "Telephony failure (FAILED expected)",
        "provider_final_state": "failed",
        "turns_template": lambda c: [
            _mk("system_event", "Call attempted. SIMULATED.", 1),
            _mk("system_event", "Twilio reported provider state: failed. SIMULATED.", 2),
        ],
    },
}


def list_scenarios() -> list[dict]:
    return [{"key": k, "label": v["label"]} for k, v in SCENARIOS.items()]


def render_scenario(key: str, contract: dict) -> dict:
    scen = SCENARIOS.get(key) or SCENARIOS["cooperative"]
    return {
        "key": key,
        "label": scen["label"],
        "provider_final_state": scen["provider_final_state"],
        "turns": scen["turns_template"](contract),
    }
