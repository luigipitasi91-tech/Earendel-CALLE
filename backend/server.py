"""
Future Call AI backend.

Vertical slice:
  REQUEST -> GOAL CONTRACT -> GUARDIAN APPROVAL -> CALL -> EVIDENCE -> VERIFY -> RESULT

Core invariants enforced:
  * No execution without explicit consent.
  * Revoked consent halts execution.
  * Recipient cannot expand permissions (Guardian block).
  * Provider "completed" != VERIFIED SUCCESS.
  * WebSocket failure never produces VERIFIED SUCCESS.
  * Callbacks are idempotent and tolerate out-of-order arrival.
"""
from __future__ import annotations

import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware

import twilio_service
import llm_service
import simulator
import verify_engine as vengine


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[os.environ["DB_NAME"]]

app = FastAPI(title="Future Call AI")
api = APIRouter(prefix="/api")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


async def _get_or_404(coll: str, _id: str) -> dict:
    doc = await db[coll].find_one({"id": _id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, f"{coll[:-1]} not found")
    return doc


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class SuccessCondition(BaseModel):
    id: str
    text: str
    kind: str = "affirmative"
    keywords: list[str] = []


class Contract(BaseModel):
    id: str = Field(default_factory=_uid)
    request_text: str = ""
    goal: str = ""
    preferred_outcome: str = ""
    hard_constraints: list[str] = []
    permitted_data: list[str] = []
    forbidden_data: list[str] = []
    forbidden_actions: list[str] = []
    success_conditions: list[SuccessCondition] = []
    recipient_number: str = ""
    consent_granted: bool = False
    consent_revoked: bool = False
    consent_at: Optional[str] = None
    created_at: str = Field(default_factory=_now_iso)


class RequestPayload(BaseModel):
    request_text: str


class ConsentPayload(BaseModel):
    granted: bool
    recipient_number: str = ""


class ExecutePayload(BaseModel):
    mode: str = "SIMULATED"          # "SIMULATED" or "REAL"
    scenario: str = "cooperative"    # only used for SIMULATED
    recipient_number: str = ""       # required for REAL
    transport: str = "TWILIO_TRIAL_GATHER"  # or "TWILIO_CONVERSATION_RELAY"


# ---------------------------------------------------------------------------
# Health / status
# ---------------------------------------------------------------------------
@api.get("/")
async def root():
    return {"service": "future-call-ai", "status": "ok"}


@api.get("/telephony/status")
async def telephony_status():
    st = twilio_service.telephony_status()
    st["llm_configured"] = bool((os.environ.get("EMERGENT_LLM_KEY") or "").strip())
    return st


@api.get("/simulator/scenarios")
async def simulator_scenarios():
    return {"scenarios": simulator.list_scenarios()}


# ---------------------------------------------------------------------------
# Goal Contract
# ---------------------------------------------------------------------------
@api.post("/contracts")
async def create_contract(payload: RequestPayload):
    if not payload.request_text.strip():
        raise HTTPException(400, "request_text is required")
    extracted = await llm_service.extract_contract(payload.request_text)
    contract = Contract(
        request_text=payload.request_text.strip(),
        **{k: v for k, v in extracted.items() if k in Contract.model_fields},
    )
    doc = contract.model_dump()
    await db.contracts.insert_one({**doc})
    doc.pop("_id", None)
    return doc


@api.get("/contracts/{cid}")
async def get_contract(cid: str):
    return await _get_or_404("contracts", cid)


@api.get("/contracts/{cid}/pre_check")
async def contract_pre_check(cid: str, mode: str = Query("SIMULATED")):
    contract = await _get_or_404("contracts", cid)
    return vengine.pre_execution_check(
        contract, mode=mode, recipient_number=contract.get("recipient_number", "")
    )


@api.put("/contracts/{cid}")
async def update_contract(cid: str, payload: dict):
    existing = await _get_or_404("contracts", cid)
    # Immutable fields
    for k in ("id", "created_at", "consent_granted", "consent_revoked", "consent_at"):
        payload.pop(k, None)
    existing.update({k: v for k, v in payload.items() if k in Contract.model_fields})
    # coerce success_conditions
    existing["success_conditions"] = [
        SuccessCondition(**c).model_dump() for c in (existing.get("success_conditions") or [])
    ]
    await db.contracts.update_one({"id": cid}, {"$set": existing})
    existing.pop("_id", None)
    return existing


# ---------------------------------------------------------------------------
# Guardian: consent
# ---------------------------------------------------------------------------
@api.post("/contracts/{cid}/consent")
async def set_consent(cid: str, payload: ConsentPayload):
    contract = await _get_or_404("contracts", cid)
    update = {
        "consent_granted": bool(payload.granted),
        "consent_at": _now_iso(),
    }
    if payload.granted:
        update["consent_revoked"] = False
        if payload.recipient_number:
            update["recipient_number"] = payload.recipient_number.strip()
    await db.contracts.update_one({"id": cid}, {"$set": update})
    contract.update(update)
    contract.pop("_id", None)
    return contract


@api.post("/contracts/{cid}/revoke")
async def revoke_consent(cid: str):
    contract = await _get_or_404("contracts", cid)
    update = {"consent_revoked": True, "consent_granted": False, "consent_at": _now_iso()}
    await db.contracts.update_one({"id": cid}, {"$set": update})
    # Also mark any active call as revoked
    await db.calls.update_many(
        {"contract_id": cid, "goal_state": {"$in": ["PENDING", "IN_PROGRESS"]}},
        {"$set": {"consent_revoked": True, "goal_state": "FAILED",
                  "verdict_reason": "User revoked consent during the call.",
                  "ended_at": _now_iso()}},
    )
    contract.update(update)
    contract.pop("_id", None)
    return contract


# ---------------------------------------------------------------------------
# Execute call: SIMULATED or REAL boundary
# ---------------------------------------------------------------------------
@api.post("/contracts/{cid}/execute")
async def execute_call(cid: str, payload: ExecutePayload):
    contract = await _get_or_404("contracts", cid)

    # Invariant: no execution without consent
    if not contract.get("consent_granted") or contract.get("consent_revoked"):
        raise HTTPException(
            403,
            "Guardian: cannot start a call without an active user consent for this contract.",
        )

    tel = twilio_service.telephony_status()
    call_id = _uid()

    if payload.mode.upper() == "REAL":
        # Choose transport (default: TRIAL_GATHER).
        transport = (payload.transport or "TWILIO_TRIAL_GATHER").upper()
        if transport not in (
            twilio_service.TRANSPORT_TRIAL_GATHER,
            twilio_service.TRANSPORT_CONVERSATION_RELAY,
        ):
            raise HTTPException(400, f"Unknown transport: {transport}")

        t_status = twilio_service.transport_status(transport)
        if t_status["status"] != "CONFIG_VALID":
            raise HTTPException(
                400,
                f"{transport} is NOT_CONFIGURED. Missing: {', '.join(t_status['missing'])}. "
                f"Cannot execute a REAL call.",
            )

        recipient = (payload.recipient_number or contract.get("recipient_number") or "").strip()
        if not recipient:
            raise HTTPException(400, "recipient_number is required for a REAL call.")
        if not twilio_service.is_valid_e164(recipient):
            raise HTTPException(
                400,
                "recipient_number must be a valid E.164 phone number (e.g. +14155552671).",
            )

        public_base = os.environ["PUBLIC_BASE_URL"].rstrip("/")
        status_cb = f"{public_base}/api/twilio/status?call_id={call_id}"
        if transport == twilio_service.TRANSPORT_TRIAL_GATHER:
            twiml_url = f"{public_base}/api/twilio/trial_gather/voice?call_id={call_id}"
        else:
            twiml_url = f"{public_base}/api/twilio/voice?call_id={call_id}"

        try:
            started = twilio_service.start_outbound_call(
                to_number=recipient,
                twiml_url=twiml_url,
                status_callback_url=status_cb,
            )
        except Exception as e:
            raise HTTPException(502, f"Failed to start Twilio call: {e}")
        call_doc = {
            "id": call_id,
            "contract_id": cid,
            "mode": "REAL",
            "transport": transport,
            "recipient_number": recipient,
            "twilio_call_sid": started["call_sid"],
            "provider_state": started["status"],
            "provider_events": [],
            "seen_events": [],
            "transcript": [],
            "goal_state": "IN_PROGRESS",
            "verdict": None,
            "verdict_reason": None,
            "guardian_blocks": [],
            "websocket_failed": False,
            "consent_revoked": False,
            "created_at": _now_iso(),
            "ended_at": None,
        }
        await db.calls.insert_one({**call_doc})
        call_doc.pop("_id", None)
        return call_doc

    # ---- SIMULATED ----
    scenario = simulator.render_scenario(payload.scenario, contract)
    transcript = scenario["turns"]

    # Guardian pass: mark forbidden probes as blocked (informational)
    guardian_blocks = []
    for turn in transcript:
        if turn.get("role") == "recipient":
            hit = vengine.recipient_wants_forbidden(
                turn.get("text", ""),
                contract.get("forbidden_actions", []),
                contract.get("forbidden_data", []),
            )
            if hit:
                guardian_blocks.append({"seq": turn.get("seq"), "matched": hit, "at": _now_iso()})

    provider_final = scenario["provider_final_state"]
    provider_failed = provider_final in ("failed", "busy", "no-answer", "canceled")

    verdict = vengine.verify(
        contract=contract,
        transcript=transcript,
        provider_state=provider_final,
        consent_revoked=False,
        provider_failed=provider_failed,
        websocket_failed=False,
        guardian_blocks=guardian_blocks,
    )

    pre_check = vengine.pre_execution_check(contract, mode="SIMULATED", recipient_number=payload.recipient_number)

    call_doc = {
        "id": call_id,
        "contract_id": cid,
        "mode": "SIMULATED",
        "scenario": payload.scenario,
        "scenario_label": scenario["label"],
        "recipient_number": (payload.recipient_number or contract.get("recipient_number") or ""),
        "twilio_call_sid": None,
        "provider_state": provider_final,
        "provider_events": [{"event": "simulated", "state": provider_final, "at": _now_iso()}],
        "seen_events": [],
        "transcript": transcript,
        "goal_state": verdict["verdict"],
        "verdict": verdict,
        "verdict_reason": verdict["reason"],
        "guardian_blocks": guardian_blocks,
        "websocket_failed": False,
        "consent_revoked": False,
        "pre_execution_check": pre_check,
        "created_at": _now_iso(),
        "ended_at": _now_iso(),
    }
    await db.calls.insert_one({**call_doc})
    call_doc.pop("_id", None)
    return call_doc


@api.get("/calls/{call_id}")
async def get_call(call_id: str):
    return await _get_or_404("calls", call_id)


@api.get("/calls")
async def list_calls(contract_id: str = Query(None)):
    q = {"contract_id": contract_id} if contract_id else {}
    docs = await db.calls.find(q, {"_id": 0}).sort("created_at", -1).to_list(200)
    return docs


@api.post("/calls/{call_id}/verify")
async def reverify_call(call_id: str):
    """Re-run the deterministic Verify Engine against the stored transcript."""
    call = await _get_or_404("calls", call_id)
    contract = await _get_or_404("contracts", call["contract_id"])
    verdict = vengine.verify(
        contract=contract,
        transcript=call.get("transcript", []),
        provider_state=call.get("provider_state") or "unknown",
        consent_revoked=bool(call.get("consent_revoked")),
        provider_failed=(call.get("provider_state") in ("failed", "busy", "no-answer", "canceled")),
        websocket_failed=bool(call.get("websocket_failed")),
        guardian_blocks=call.get("guardian_blocks") or [],
    )
    await db.calls.update_one(
        {"id": call_id},
        {"$set": {
            "verdict": verdict,
            "goal_state": verdict["verdict"],
            "verdict_reason": verdict["reason"],
        }},
    )
    call.update({"verdict": verdict, "goal_state": verdict["verdict"], "verdict_reason": verdict["reason"]})
    call.pop("_id", None)
    return call


# ---------------------------------------------------------------------------
# Twilio: REAL boundary
# ---------------------------------------------------------------------------
def _rebuild_url(request: Request) -> str:
    # Use PUBLIC_BASE_URL if set so signature matches what Twilio signed.
    base = (os.environ.get("PUBLIC_BASE_URL") or "").rstrip("/")
    if base:
        return f"{base}{request.url.path}?{request.url.query}" if request.url.query else f"{base}{request.url.path}"
    return str(request.url)


@api.post("/twilio/voice")
async def twilio_voice(request: Request, call_id: str = Query(...)):
    """
    Return TwiML: <Connect><ConversationRelay ... /></Connect>.
    Validates X-Twilio-Signature when Twilio is configured.
    """
    form = dict((await request.form()).items()) if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded") else {}
    sig = request.headers.get("X-Twilio-Signature")
    url = _rebuild_url(request)

    if twilio_service.is_configured():
        if not twilio_service.validate_http_signature(url, form, sig):
            raise HTTPException(403, "Invalid Twilio signature")

    call = await db.calls.find_one({"id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(404, "call not found")
    contract = await db.contracts.find_one({"id": call["contract_id"]}, {"_id": 0}) or {}

    if contract.get("consent_revoked"):
        # Consent already revoked: refuse to proceed with the call.
        twiml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response><Hangup/></Response>"
        return Response(content=twiml, media_type="application/xml")

    greeting = f"Hello, this is an authorized assistant calling regarding: {contract.get('goal') or 'a scheduled appointment'}."
    public_base = (os.environ.get("PUBLIC_BASE_URL") or "").rstrip("/")
    status_url = f"{public_base}/api/twilio/status?call_id={call_id}"

    twiml = twilio_service.build_conversation_relay_twiml(
        welcome_greeting=greeting,
        status_callback_url=status_url,
    )
    return Response(content=twiml, media_type="application/xml")


# --- TWILIO_TRIAL_GATHER transport --------------------------------------

def _trial_gather_prompt(contract: dict) -> str:
    """
    Build the recipient-facing prompt. Contains ONLY information the user
    has permitted (goal, permitted_data). Forbidden data is never spoken.
    """
    goal = (contract.get("goal") or "regarding a scheduled matter").strip().rstrip(".")
    permitted = contract.get("permitted_data") or []
    parts = [f"Hello. This is an authorized assistant calling {goal}."]
    if permitted:
        parts.append("For your records I may reference: " + ", ".join(permitted) + ".")
    parts.append(
        "Could you please confirm the outcome after the tone? "
        "Please speak clearly after the beep."
    )
    return " ".join(parts)


@api.post("/twilio/trial_gather/voice")
async def twilio_trial_gather_voice(request: Request, call_id: str = Query(...)):
    """
    TwiML entry point for the TWILIO_TRIAL_GATHER transport. Returns
    <Say> + <Gather input="speech"> pointing at /twilio/trial_gather/speech.
    """
    form = dict((await request.form()).items()) if request.headers.get("content-type", "").startswith("application/x-www-form-urlencoded") else {}
    sig = request.headers.get("X-Twilio-Signature")
    url = _rebuild_url(request)

    if twilio_service.is_configured(twilio_service.TRANSPORT_TRIAL_GATHER):
        if not twilio_service.validate_http_signature(url, form, sig):
            raise HTTPException(403, "Invalid Twilio signature")

    call = await db.calls.find_one({"id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(404, "call not found")
    contract = await db.contracts.find_one({"id": call["contract_id"]}, {"_id": 0}) or {}

    if contract.get("consent_revoked") or not contract.get("consent_granted"):
        twiml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Response><Hangup/></Response>"
        return Response(content=twiml, media_type="application/xml")

    public_base = (os.environ.get("PUBLIC_BASE_URL") or "").rstrip("/")
    action_url = f"{public_base}/api/twilio/trial_gather/speech?call_id={call_id}&gather_seq=1"
    say_text = _trial_gather_prompt(contract)

    twiml = twilio_service.build_trial_gather_twiml(
        say_text=say_text,
        action_url=action_url,
    )
    return Response(content=twiml, media_type="application/xml")


@api.post("/twilio/trial_gather/speech")
async def twilio_trial_gather_speech(
    request: Request,
    call_id: str = Query(...),
    gather_seq: int = Query(1),
):
    """
    Twilio <Gather> action callback. Idempotent by (CallSid, gather_seq).
    Normalizes SpeechResult into a recipient transcript turn with explicit
    provenance (source=twilio, transport=TWILIO_TRIAL_GATHER). Returns
    follow-up TwiML that ends the call politely.
    """
    form = dict((await request.form()).items())
    sig = request.headers.get("X-Twilio-Signature")
    url = _rebuild_url(request)

    if twilio_service.is_configured(twilio_service.TRANSPORT_TRIAL_GATHER):
        if not twilio_service.validate_http_signature(url, form, sig):
            raise HTTPException(403, "Invalid Twilio signature")

    call = await db.calls.find_one({"id": call_id}, {"_id": 0})
    if not call:
        raise HTTPException(404, "call not found")

    call_sid = form.get("CallSid") or ""
    event_key = f"{call_sid}:gather:{int(gather_seq)}"

    # Idempotency: dedupe duplicate/replayed webhook deliveries.
    if event_key in (call.get("seen_events") or []):
        # Return a benign hangup TwiML — evidence already recorded.
        return Response(
            content=twilio_service.build_trial_gather_ack_twiml(
                say_text="Thank you. Goodbye."
            ),
            media_type="application/xml",
        )

    speech = (form.get("SpeechResult") or "").strip()
    confidence_raw = form.get("Confidence")
    try:
        confidence = float(confidence_raw) if confidence_raw is not None else None
    except ValueError:
        confidence = None

    updates: dict[str, Any] = {
        "$push": {
            "seen_events": event_key,
            "provider_events": {
                "event": "gather",
                "seq": int(gather_seq),
                "at": _now_iso(),
                "call_sid": call_sid,
                "had_speech": bool(speech),
            },
        }
    }

    if speech:
        turn = {
            "seq": int(gather_seq),
            "role": "recipient",
            "text": speech,
            "at": _now_iso(),
            "mode": "REAL",
            "provenance": {
                "source": "twilio",
                "transport": twilio_service.TRANSPORT_TRIAL_GATHER,
                "call_sid": call_sid,
                "gather_seq": int(gather_seq),
                "confidence": confidence,
            },
        }
        updates["$push"]["transcript"] = turn

    await db.calls.update_one({"id": call_id}, updates)

    # Re-run verification with the updated evidence, but NEVER treat provider
    # completion as goal success. Empty speech leaves the goal state UNKNOWN.
    fresh = await db.calls.find_one({"id": call_id}, {"_id": 0})
    contract = await db.contracts.find_one({"id": fresh["contract_id"]}, {"_id": 0}) or {}
    verdict = vengine.verify(
        contract=contract,
        transcript=fresh.get("transcript", []),
        provider_state=fresh.get("provider_state") or "in-progress",
        consent_revoked=bool(fresh.get("consent_revoked")),
        provider_failed=False,
        websocket_failed=False,
        guardian_blocks=fresh.get("guardian_blocks") or [],
    )
    await db.calls.update_one(
        {"id": call_id},
        {"$set": {
            "verdict": verdict,
            "goal_state": verdict["verdict"],
            "verdict_reason": verdict["reason"],
        }},
    )

    ack = (
        "Thank you. We have recorded your response. Goodbye."
        if speech else
        "We did not receive a response. Ending the call."
    )
    return Response(
        content=twilio_service.build_trial_gather_ack_twiml(say_text=ack),
        media_type="application/xml",
    )


@api.post("/twilio/status")
async def twilio_status(request: Request, call_id: str = Query(...)):
    """
    Idempotent Twilio status callback.
    Dedupes by (CallSid, SequenceNumber, CallStatus). Out-of-order safe:
    a lower SequenceNumber must NOT roll state backwards.
    """
    form = dict((await request.form()).items())
    sig = request.headers.get("X-Twilio-Signature")
    url = _rebuild_url(request)

    if twilio_service.is_configured():
        if not twilio_service.validate_http_signature(url, form, sig):
            raise HTTPException(403, "Invalid Twilio signature")

    call = await db.calls.find_one({"id": call_id}, {"_id": 0})
    if not call:
        return PlainTextResponse("ok")

    call_sid = form.get("CallSid") or ""
    seq_raw = form.get("SequenceNumber")
    try:
        seq = int(seq_raw) if seq_raw is not None else -1
    except ValueError:
        seq = -1
    status = form.get("CallStatus") or form.get("status") or ""
    event_key = f"{call_sid}:{seq}:{status}"

    # Idempotency: skip if we've already processed this exact event.
    if event_key in (call.get("seen_events") or []):
        return PlainTextResponse("ok")

    # Ordering guard: track highest seq applied to provider_state.
    highest = call.get("provider_state_seq", -1)
    updates: dict[str, Any] = {
        "$push": {
            "provider_events": {"event": "status", "seq": seq, "state": status, "at": _now_iso(), "raw": form},
            "seen_events": event_key,
        }
    }
    if seq > highest:
        updates["$set"] = {"provider_state": status, "provider_state_seq": seq}
        if status in ("completed", "failed", "busy", "no-answer", "canceled"):
            updates["$set"]["ended_at"] = _now_iso()

    await db.calls.update_one({"id": call_id}, updates)

    # If terminal, run verify.
    if status in ("completed", "failed", "busy", "no-answer", "canceled"):
        fresh = await db.calls.find_one({"id": call_id}, {"_id": 0})
        contract = await db.contracts.find_one({"id": fresh["contract_id"]}, {"_id": 0}) or {}
        verdict = vengine.verify(
            contract=contract,
            transcript=fresh.get("transcript", []),
            provider_state=fresh.get("provider_state") or status,
            consent_revoked=bool(fresh.get("consent_revoked")),
            provider_failed=(status in ("failed", "busy", "no-answer", "canceled")),
            websocket_failed=bool(fresh.get("websocket_failed")),
            guardian_blocks=fresh.get("guardian_blocks") or [],
        )
        await db.calls.update_one(
            {"id": call_id},
            {"$set": {
                "verdict": verdict,
                "goal_state": verdict["verdict"],
                "verdict_reason": verdict["reason"],
            }},
        )

    return PlainTextResponse("ok")


# ---------------------------------------------------------------------------
# ConversationRelay WebSocket
# ---------------------------------------------------------------------------
@app.websocket("/api/twilio/relay")
async def twilio_relay(ws: WebSocket):
    """
    ConversationRelay WebSocket endpoint.

    Real integration boundary: validates X-Twilio-Signature on the handshake
    when Twilio is configured, else accepts only if simulation testing is
    explicitly enabled by absent credentials + label everything SIMULATED.
    Malformed frames are handled safely and never produce goal state.
    """
    sig = ws.headers.get("x-twilio-signature")
    # ws.url gives ws://... — for signature validation Twilio expects the wss URL used.
    url = (os.environ.get("TWILIO_CONVERSATION_RELAY_WSS_URL") or "").strip() or str(ws.url).replace("ws://", "wss://")

    if twilio_service.is_configured():
        if not twilio_service.validate_relay_handshake(url, sig):
            await ws.close(code=4403)
            return

    await ws.accept()
    call_id: Optional[str] = None
    try:
        while True:
            msg = await ws.receive_json()
            mtype = msg.get("type")

            # ConversationRelay "setup" carries CallSid and custom parameters.
            if mtype == "setup":
                call_sid = msg.get("callSid") or msg.get("CallSid")
                cp = msg.get("customParameters") or {}
                call_id = cp.get("call_id") or msg.get("call_id")
                if call_id:
                    await db.calls.update_one(
                        {"id": call_id},
                        {"$set": {"twilio_call_sid": call_sid, "provider_state": "in-progress"}},
                    )

            elif mtype in ("prompt", "transcript"):
                # recipient (human) turn as detected by CR speech-to-text
                text = msg.get("voicePrompt") or msg.get("transcript") or ""
                if call_id and text:
                    await db.calls.update_one(
                        {"id": call_id},
                        {"$push": {"transcript": {
                            "seq": msg.get("last") or -1,
                            "role": "recipient",
                            "text": text,
                            "at": _now_iso(),
                            "mode": "REAL",
                        }}},
                    )

            elif mtype == "dtmf":
                if call_id:
                    await db.calls.update_one(
                        {"id": call_id},
                        {"$push": {"transcript": {"role": "system_event",
                                                  "text": f"DTMF: {msg.get('digit')}",
                                                  "at": _now_iso(), "mode": "REAL"}}},
                    )

            elif mtype == "interrupt":
                if call_id:
                    await db.calls.update_one(
                        {"id": call_id},
                        {"$push": {"transcript": {"role": "system_event",
                                                  "text": "Recipient interrupted.",
                                                  "at": _now_iso(), "mode": "REAL"}}},
                    )

            elif mtype == "error":
                if call_id:
                    await db.calls.update_one(
                        {"id": call_id},
                        {"$push": {"transcript": {"role": "system_event",
                                                  "text": f"ConversationRelay error: {msg.get('description')}",
                                                  "at": _now_iso(), "mode": "REAL"}}},
                    )

            # Unknown types are ignored safely.

    except WebSocketDisconnect:
        if call_id:
            await db.calls.update_one({"id": call_id}, {"$set": {"websocket_failed": False}})
    except Exception as e:
        logging.exception("Relay WS error: %s", e)
        if call_id:
            await db.calls.update_one({"id": call_id}, {"$set": {"websocket_failed": True}})


# ---------------------------------------------------------------------------
# Wire router + middleware
# ---------------------------------------------------------------------------
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


@app.on_event("shutdown")
async def shutdown():
    mongo_client.close()
