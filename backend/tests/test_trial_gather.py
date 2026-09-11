"""
Tests for the TWILIO_TRIAL_GATHER transport.

- Uses httpx.AsyncClient with an in-process ASGI transport (no real HTTP).
- Uses `mongomock_motor.AsyncMongoMockClient` in place of the module-level
  motor client so tests are isolated and safe against event-loop reuse.
- Mocks the outbound-call adapter (`twilio_service.start_outbound_call`) so no
  real Twilio API is invoked and no credits are consumed.
- Uses monkeypatched env vars for CONFIG_VALID scenarios — no real credentials
  ever appear in this file or in test output.
"""
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import server  # noqa: E402
import twilio_service as ts  # noqa: E402


BASE = {
    "TWILIO_ACCOUNT_SID": "AC_placeholder",
    "TWILIO_AUTH_TOKEN": "tok_placeholder",
    "TWILIO_FROM_NUMBER": "+10000000000",
    "PUBLIC_BASE_URL": "https://example.test",
}


@pytest_asyncio.fixture(autouse=True)
async def isolated_db(monkeypatch):
    """Replace the module-level motor client with a per-test mongomock client."""
    fake_client = AsyncMongoMockClient()
    fake_db = fake_client["test_db"]
    monkeypatch.setattr(server, "db", fake_db)
    yield fake_db


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=server.app), base_url="http://test") as ac:
        yield ac


def _clear_env(monkeypatch):
    for k in list(BASE.keys()) + ["TWILIO_CONVERSATION_RELAY_WSS_URL"]:
        monkeypatch.delenv(k, raising=False)


def _set_env(monkeypatch, mapping):
    _clear_env(monkeypatch)
    for k, v in mapping.items():
        monkeypatch.setenv(k, v)


async def _make_contract(client, consent=True):
    r = await client.post(
        "/api/contracts",
        json={"request_text": "Move my appointment to Friday afternoon, but only if there is no additional charge."},
    )
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    if consent:
        r2 = await client.post(f"/api/contracts/{cid}/consent", json={"granted": True})
        assert r2.status_code == 200
    return cid


# A. CONFIG_VALID for TRIAL_GATHER without ConversationRelay WSS
def test_trial_gather_config_valid_without_relay_wss(monkeypatch):
    _set_env(monkeypatch, BASE)
    st = ts.transport_status(ts.TRANSPORT_TRIAL_GATHER)
    assert st["status"] == "CONFIG_VALID"
    assert ts.is_configured(ts.TRANSPORT_TRIAL_GATHER) is True


# B. Missing config prevents execution
@pytest.mark.asyncio
async def test_missing_config_blocks_real_execute(client, monkeypatch):
    _clear_env(monkeypatch)
    cid = await _make_contract(client, consent=True)
    r = await client.post(
        f"/api/contracts/{cid}/execute",
        json={"mode": "REAL", "transport": "TWILIO_TRIAL_GATHER", "recipient_number": "+14155552671"},
    )
    assert r.status_code == 400
    assert "NOT_CONFIGURED" in r.text


# C. No consent -> blocked
@pytest.mark.asyncio
async def test_no_consent_blocks_outbound(client, monkeypatch):
    _set_env(monkeypatch, BASE)
    cid = await _make_contract(client, consent=False)
    r = await client.post(
        f"/api/contracts/{cid}/execute",
        json={"mode": "REAL", "transport": "TWILIO_TRIAL_GATHER", "recipient_number": "+14155552671"},
    )
    assert r.status_code == 403
    assert "consent" in r.text.lower()


# D. Guardian denial (revoked consent) -> blocked
@pytest.mark.asyncio
async def test_revoked_consent_blocks_outbound(client, monkeypatch):
    _set_env(monkeypatch, BASE)
    cid = await _make_contract(client, consent=True)
    await client.post(f"/api/contracts/{cid}/revoke")
    r = await client.post(
        f"/api/contracts/{cid}/execute",
        json={"mode": "REAL", "transport": "TWILIO_TRIAL_GATHER", "recipient_number": "+14155552671"},
    )
    assert r.status_code == 403


# K. Invalid E.164 rejected BEFORE any provider invocation
@pytest.mark.parametrize("bad", ["12345", "not a number", "+", "+abc", "+0123456789", ""])
@pytest.mark.asyncio
async def test_invalid_recipient_rejected(client, monkeypatch, bad):
    _set_env(monkeypatch, BASE)
    called = {"n": 0}

    def _spy(**_):
        called["n"] += 1
        return {"call_sid": "CA_fake", "status": "queued"}

    monkeypatch.setattr(ts, "start_outbound_call", _spy)

    cid = await _make_contract(client, consent=True)
    r = await client.post(
        f"/api/contracts/{cid}/execute",
        json={"mode": "REAL", "transport": "TWILIO_TRIAL_GATHER", "recipient_number": bad},
    )
    assert r.status_code == 400, r.text
    assert called["n"] == 0, "start_outbound_call must not be invoked for invalid numbers"


# E. Generated TwiML contains Say + Gather with correct callback path
@pytest.mark.asyncio
async def test_trial_gather_voice_returns_say_and_gather(client, monkeypatch):
    _set_env(monkeypatch, BASE)
    monkeypatch.setattr(ts, "start_outbound_call", lambda **_: {"call_sid": "CAtest123", "status": "queued"})

    cid = await _make_contract(client, consent=True)
    r = await client.post(
        f"/api/contracts/{cid}/execute",
        json={"mode": "REAL", "transport": "TWILIO_TRIAL_GATHER", "recipient_number": "+14155552671"},
    )
    assert r.status_code == 200, r.text
    call = r.json()
    assert call["transport"] == "TWILIO_TRIAL_GATHER"
    assert call["twilio_call_sid"] == "CAtest123"
    call_id = call["id"]

    # Bypass signature validation by clearing AUTH_TOKEN before the TwiML GET.
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    r2 = await client.post(f"/api/twilio/trial_gather/voice?call_id={call_id}", data={})
    assert r2.status_code == 200
    body = r2.text
    assert "<Say" in body
    assert "<Gather" in body
    assert 'input="speech"' in body
    assert f"/api/twilio/trial_gather/speech?call_id={call_id}" in body


# F. Gathered speech becomes evidence with provenance
@pytest.mark.asyncio
async def test_speech_becomes_evidence_with_provenance(client, monkeypatch):
    _set_env(monkeypatch, BASE)
    monkeypatch.setattr(ts, "start_outbound_call", lambda **_: {"call_sid": "CAX1", "status": "queued"})

    cid = await _make_contract(client, consent=True)
    r = await client.post(
        f"/api/contracts/{cid}/execute",
        json={"mode": "REAL", "transport": "TWILIO_TRIAL_GATHER", "recipient_number": "+14155552671"},
    )
    call_id = r.json()["id"]

    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    speech = "Yes, your appointment is rescheduled to Friday afternoon and there is no additional charge."
    r2 = await client.post(
        f"/api/twilio/trial_gather/speech?call_id={call_id}&gather_seq=1",
        data={"CallSid": "CAX1", "SpeechResult": speech, "Confidence": "0.92"},
    )
    assert r2.status_code == 200

    call = (await client.get(f"/api/calls/{call_id}")).json()
    turns = [t for t in call.get("transcript", []) if t["role"] == "recipient"]
    assert len(turns) == 1
    t = turns[0]
    assert t["text"] == speech
    assert t["mode"] == "REAL"
    assert t["provenance"]["source"] == "twilio"
    assert t["provenance"]["transport"] == "TWILIO_TRIAL_GATHER"
    assert t["provenance"]["call_sid"] == "CAX1"
    assert t["provenance"]["gather_seq"] == 1


# G. Empty/ambiguous speech cannot produce VERIFIED_SUCCESS
@pytest.mark.asyncio
async def test_empty_speech_cannot_produce_verified_success(client, monkeypatch):
    _set_env(monkeypatch, BASE)
    monkeypatch.setattr(ts, "start_outbound_call", lambda **_: {"call_sid": "CAX2", "status": "queued"})
    cid = await _make_contract(client, consent=True)
    r = await client.post(
        f"/api/contracts/{cid}/execute",
        json={"mode": "REAL", "transport": "TWILIO_TRIAL_GATHER", "recipient_number": "+14155552671"},
    )
    call_id = r.json()["id"]

    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    r2 = await client.post(
        f"/api/twilio/trial_gather/speech?call_id={call_id}&gather_seq=1",
        data={"CallSid": "CAX2", "SpeechResult": "", "Confidence": "0.0"},
    )
    assert r2.status_code == 200
    call = (await client.get(f"/api/calls/{call_id}")).json()
    assert call["goal_state"] != "VERIFIED_SUCCESS"

    r3 = await client.post(
        f"/api/twilio/trial_gather/speech?call_id={call_id}&gather_seq=2",
        data={"CallSid": "CAX2", "SpeechResult": "Friday afternoon works.", "Confidence": "0.8"},
    )
    assert r3.status_code == 200
    call2 = (await client.get(f"/api/calls/{call_id}")).json()
    assert call2["goal_state"] != "VERIFIED_SUCCESS"


# H. Provider "completed" without evidence != VERIFIED_SUCCESS
@pytest.mark.asyncio
async def test_provider_completed_without_evidence_is_not_success(client, monkeypatch):
    _set_env(monkeypatch, BASE)
    monkeypatch.setattr(ts, "start_outbound_call", lambda **_: {"call_sid": "CAX3", "status": "queued"})
    cid = await _make_contract(client, consent=True)
    r = await client.post(
        f"/api/contracts/{cid}/execute",
        json={"mode": "REAL", "transport": "TWILIO_TRIAL_GATHER", "recipient_number": "+14155552671"},
    )
    call_id = r.json()["id"]

    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    r2 = await client.post(
        f"/api/twilio/status?call_id={call_id}",
        data={"CallSid": "CAX3", "SequenceNumber": "5", "CallStatus": "completed"},
    )
    assert r2.status_code == 200
    call = (await client.get(f"/api/calls/{call_id}")).json()
    assert call["provider_state"] == "completed"
    assert call["goal_state"] != "VERIFIED_SUCCESS"


# I. Explicit provider failure -> FAILED via existing rules
@pytest.mark.asyncio
async def test_provider_failure_yields_failed(client, monkeypatch):
    _set_env(monkeypatch, BASE)
    monkeypatch.setattr(ts, "start_outbound_call", lambda **_: {"call_sid": "CAX4", "status": "queued"})
    cid = await _make_contract(client, consent=True)
    r = await client.post(
        f"/api/contracts/{cid}/execute",
        json={"mode": "REAL", "transport": "TWILIO_TRIAL_GATHER", "recipient_number": "+14155552671"},
    )
    call_id = r.json()["id"]

    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    r2 = await client.post(
        f"/api/twilio/status?call_id={call_id}",
        data={"CallSid": "CAX4", "SequenceNumber": "1", "CallStatus": "failed"},
    )
    assert r2.status_code == 200
    call = (await client.get(f"/api/calls/{call_id}")).json()
    assert call["goal_state"] == "FAILED"


# J. Duplicate webhook does not duplicate evidence or change verdict
@pytest.mark.asyncio
async def test_duplicate_speech_webhook_is_idempotent(client, monkeypatch):
    _set_env(monkeypatch, BASE)
    monkeypatch.setattr(ts, "start_outbound_call", lambda **_: {"call_sid": "CAX5", "status": "queued"})
    cid = await _make_contract(client, consent=True)
    r = await client.post(
        f"/api/contracts/{cid}/execute",
        json={"mode": "REAL", "transport": "TWILIO_TRIAL_GATHER", "recipient_number": "+14155552671"},
    )
    call_id = r.json()["id"]

    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    payload = {"CallSid": "CAX5", "SpeechResult": "Confirmed, your appointment is moved to Friday afternoon and there is no additional charge.", "Confidence": "0.95"}
    r2 = await client.post(f"/api/twilio/trial_gather/speech?call_id={call_id}&gather_seq=1", data=payload)
    r3 = await client.post(f"/api/twilio/trial_gather/speech?call_id={call_id}&gather_seq=1", data=payload)
    assert r2.status_code == 200 and r3.status_code == 200
    call = (await client.get(f"/api/calls/{call_id}")).json()
    turns = [t for t in call["transcript"] if t["role"] == "recipient"]
    assert len(turns) == 1

    for _ in range(3):
        await client.post(
            f"/api/twilio/status?call_id={call_id}",
            data={"CallSid": "CAX5", "SequenceNumber": "10", "CallStatus": "completed"},
        )
    call2 = (await client.get(f"/api/calls/{call_id}")).json()
    completed = [e for e in call2["provider_events"] if e.get("event") == "status" and e.get("state") == "completed"]
    assert len(completed) == 1


# Security: no credentials returned in status/API responses
@pytest.mark.asyncio
async def test_no_credentials_in_api_responses(client, monkeypatch):
    _set_env(monkeypatch, BASE)
    r = await client.get("/api/telephony/status")
    body = r.text
    assert BASE["TWILIO_ACCOUNT_SID"] not in body
    assert BASE["TWILIO_AUTH_TOKEN"] not in body
    assert BASE["TWILIO_FROM_NUMBER"] not in body
