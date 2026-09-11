"""
Twilio integration boundary for Future Call AI.

Two explicit transport modes:
  * TWILIO_TRIAL_GATHER      — <Say>/<Gather> transport (future). Does NOT
                               require TWILIO_CONVERSATION_RELAY_WSS_URL.
  * TWILIO_CONVERSATION_RELAY — WebSocket transport (future/paid). Requires
                               TWILIO_CONVERSATION_RELAY_WSS_URL.

Neither transport places a real call in this build. The transport adapter
never decides whether the user's goal succeeded — that is Verify Engine's job.

If credentials are missing, all functions still WORK enough to serve as a
boundary, but everything is flagged NOT_CONFIGURED. We never fabricate calls.
"""
from __future__ import annotations

import os
import re
from typing import Optional
from xml.sax.saxutils import escape

from twilio.request_validator import RequestValidator
from twilio.rest import Client


# --- transport identifiers (do not confuse with goal state) ----------------
TRANSPORT_TRIAL_GATHER = "TWILIO_TRIAL_GATHER"
TRANSPORT_CONVERSATION_RELAY = "TWILIO_CONVERSATION_RELAY"

BASE_REQUIRED = (
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER",
    "PUBLIC_BASE_URL",
)


def _cfg(key: str) -> str:
    return (os.environ.get(key) or "").strip()


def _missing_for(transport: str) -> list[str]:
    """Return the list of required-but-empty env vars for a transport."""
    required = list(BASE_REQUIRED)
    if transport == TRANSPORT_CONVERSATION_RELAY:
        required.append("TWILIO_CONVERSATION_RELAY_WSS_URL")
    return [k for k in required if not _cfg(k)]


def transport_status(transport: str) -> dict:
    """Config validity for a single transport. Never prints secrets."""
    missing = _missing_for(transport)
    return {
        "transport": transport,
        "status": "CONFIG_VALID" if not missing else "NOT_CONFIGURED",
        "missing": missing,
    }


def telephony_status() -> dict:
    """
    Report configuration status for BOTH transports separately.

    Overall `mode` remains for backward compatibility: REAL only when at least
    one transport is CONFIG_VALID; otherwise NOT_CONFIGURED. No real call is
    made in this build regardless of status.
    """
    trial = transport_status(TRANSPORT_TRIAL_GATHER)
    relay = transport_status(TRANSPORT_CONVERSATION_RELAY)
    any_valid = trial["status"] == "CONFIG_VALID" or relay["status"] == "CONFIG_VALID"

    return {
        # legacy top-level fields (kept for existing UI/test compatibility)
        "mode": "REAL" if any_valid else "NOT_CONFIGURED",
        "missing": _missing_for(TRANSPORT_CONVERSATION_RELAY),  # legacy default
        "signature_validation": "ENABLED" if _cfg("TWILIO_AUTH_TOKEN") else "NOT_CONFIGURED",
        # explicit per-transport report
        "transports": {
            TRANSPORT_TRIAL_GATHER: trial,
            TRANSPORT_CONVERSATION_RELAY: relay,
        },
        "from_number_set": bool(_cfg("TWILIO_FROM_NUMBER")),
        "public_base_url_set": bool(_cfg("PUBLIC_BASE_URL")),
    }


def is_configured(transport: str | None = None) -> bool:
    """
    True only if the given transport is CONFIG_VALID. When transport is None,
    True if either transport is CONFIG_VALID.
    """
    if transport is None:
        st = telephony_status()
        return any(t["status"] == "CONFIG_VALID" for t in st["transports"].values())
    return transport_status(transport)["status"] == "CONFIG_VALID"


def validate_http_signature(url: str, params: dict, signature: Optional[str]) -> bool:
    """
    Validate Twilio HTTP webhook using X-Twilio-Signature.
    Returns False if not configured or invalid.
    """
    auth_token = _cfg("TWILIO_AUTH_TOKEN")
    if not auth_token or not signature:
        return False
    validator = RequestValidator(auth_token)
    return validator.validate(url, params, signature)


def validate_relay_handshake(url: str, signature: Optional[str]) -> bool:
    """
    Validate the ConversationRelay WebSocket handshake signature.
    ConversationRelay sends X-Twilio-Signature on the HTTP Upgrade with an
    empty request body/params.
    """
    auth_token = _cfg("TWILIO_AUTH_TOKEN")
    if not auth_token or not signature:
        return False
    validator = RequestValidator(auth_token)
    return validator.validate(url, {}, signature)


def build_conversation_relay_twiml(
    *,
    welcome_greeting: str,
    status_callback_url: str,
) -> str:
    """
    Return TwiML that connects the outbound call to our ConversationRelay
    WebSocket. The wss URL is our own /api/twilio/relay endpoint by default,
    or the value of TWILIO_CONVERSATION_RELAY_WSS_URL if set explicitly.
    """
    wss_url = _cfg("TWILIO_CONVERSATION_RELAY_WSS_URL")
    if not wss_url:
        public_base = _cfg("PUBLIC_BASE_URL")
        if public_base:
            wss_url = public_base.replace("http://", "ws://").replace("https://", "wss://").rstrip("/") + "/api/twilio/relay"
        else:
            wss_url = ""

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect action="{escape(status_callback_url)}">
    <ConversationRelay
      url="{escape(wss_url)}"
      welcomeGreeting="{escape(welcome_greeting)}"
      welcomeGreetingInterruptible="true"
      interruptible="true"
      dtmfDetection="true"
      transcriptionProvider="Deepgram"
      ttsProvider="ElevenLabs"
    />
  </Connect>
</Response>"""
    return twiml


# ---------------------------------------------------------------------------
# TWILIO_TRIAL_GATHER transport: <Say> + <Gather input="speech">
# ---------------------------------------------------------------------------

# E.164: leading '+', 1-3 digit country code, up to 15 total digits.
_E164 = re.compile(r"^\+[1-9]\d{6,14}$")


def is_valid_e164(number: str) -> bool:
    return bool(_E164.match((number or "").strip()))


def build_trial_gather_twiml(
    *,
    say_text: str,
    action_url: str,
    hints: str = "",
    speech_timeout: str = "auto",
    timeout_seconds: int = 6,
    language: str = "en-US",
) -> str:
    """
    TwiML for the TRIAL_GATHER transport. Speaks `say_text` and gathers speech
    from the recipient, POSTing the SpeechResult to `action_url`.

    - method is fixed to POST (Twilio's default form-encoded webhook).
    - No sensitive user data should be embedded in `say_text`; the caller is
      responsible for constraining what is spoken.
    """
    hints_attr = f' hints="{escape(hints)}"' if hints else ""
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna" language="{escape(language)}">{escape(say_text)}</Say>
  <Gather input="speech" action="{escape(action_url)}" method="POST" language="{escape(language)}" speechTimeout="{escape(str(speech_timeout))}" timeout="{int(timeout_seconds)}"{hints_attr}/>
  <Say voice="Polly.Joanna" language="{escape(language)}">We did not receive a response. Ending the call.</Say>
  <Hangup/>
</Response>"""
    return twiml


def build_trial_gather_ack_twiml(*, say_text: str) -> str:
    """TwiML used to end the call politely after evidence has been gathered."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say voice="Polly.Joanna">{escape(say_text)}</Say>
  <Hangup/>
</Response>"""


def start_outbound_call(
    *,
    to_number: str,
    twiml_url: str,
    status_callback_url: str,
) -> dict:
    """
    Kick off a real outbound Twilio call. Raises if not configured.
    """
    status = telephony_status()
    if status["mode"] != "REAL":
        raise RuntimeError(
            f"Twilio is NOT_CONFIGURED. Missing: {', '.join(status['missing'])}"
        )
    client = Client(_cfg("TWILIO_ACCOUNT_SID"), _cfg("TWILIO_AUTH_TOKEN"))
    call = client.calls.create(
        to=to_number,
        from_=_cfg("TWILIO_FROM_NUMBER"),
        url=twiml_url,
        status_callback=status_callback_url,
        status_callback_event=[
            "initiated", "ringing", "answered", "completed",
        ],
        status_callback_method="POST",
    )
    return {"call_sid": call.sid, "status": call.status}
