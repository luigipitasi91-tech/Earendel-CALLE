"""
Twilio integration boundary for Future Call AI.

- Generates TwiML for <Connect><ConversationRelay>.
- Validates X-Twilio-Signature on HTTP webhooks and the ConversationRelay
  WebSocket handshake.
- Reports configuration status.

If credentials are missing, all functions still WORK enough to serve as a
boundary, but everything is flagged NOT_CONFIGURED. We never fabricate calls.
"""
from __future__ import annotations

import os
from typing import Optional
from xml.sax.saxutils import escape

from twilio.request_validator import RequestValidator
from twilio.rest import Client


def _cfg(key: str) -> str:
    return (os.environ.get(key) or "").strip()


def telephony_status() -> dict:
    account_sid = _cfg("TWILIO_ACCOUNT_SID")
    auth_token = _cfg("TWILIO_AUTH_TOKEN")
    from_number = _cfg("TWILIO_FROM_NUMBER")
    public_base = _cfg("PUBLIC_BASE_URL")
    wss_url = _cfg("TWILIO_CONVERSATION_RELAY_WSS_URL")

    missing = []
    if not account_sid:
        missing.append("TWILIO_ACCOUNT_SID")
    if not auth_token:
        missing.append("TWILIO_AUTH_TOKEN")
    if not from_number:
        missing.append("TWILIO_FROM_NUMBER")
    if not public_base:
        missing.append("PUBLIC_BASE_URL")
    if not wss_url:
        missing.append("TWILIO_CONVERSATION_RELAY_WSS_URL")

    return {
        "mode": "REAL" if not missing else "NOT_CONFIGURED",
        "missing": missing,
        "public_base_url": public_base or None,
        "conversation_relay_wss_url": wss_url or None,
        "from_number": from_number or None,
        "signature_validation": "ENABLED" if auth_token else "NOT_CONFIGURED",
    }


def is_configured() -> bool:
    return telephony_status()["mode"] == "REAL"


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
