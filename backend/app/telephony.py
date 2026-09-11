import os
from dataclasses import dataclass

@dataclass
class TelephonyReadiness:
    mode: str
    configured: bool
    missing: list[str]
    note: str

REQUIRED_TWILIO = [
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER",
    "PUBLIC_BASE_URL",
]

def readiness() -> TelephonyReadiness:
    missing = [k for k in REQUIRED_TWILIO if not os.getenv(k)]
    if missing:
        return TelephonyReadiness(
            mode="NOT_CONFIGURED",
            configured=False,
            missing=missing,
            note="Live telephony is not configured. Simulation is allowed only when visibly labelled."
        )
    return TelephonyReadiness(
        mode="READY_FOR_CONTROLLED_TRIAL",
        configured=True,
        missing=[],
        note="Credentials exist; a real controlled provider test is still required before claiming LIVE."
    )

def twilio_trial_capabilities():
    return {
        "supported_test_path": ["outbound_call", "Say", "Gather(speech/dtmf)", "status_callbacks"],
        "blocked_on_trial": ["ConversationRelay", "MediaStreams", "Record"],
        "claim": "This adapter is only a readiness boundary; it does not claim a live call succeeded."
    }
