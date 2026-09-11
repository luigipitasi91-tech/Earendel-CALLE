"""
Config-boundary tests for the Twilio transport adapter.

These tests toggle env vars via monkeypatch and never write real credentials.
They do NOT place any real call. They do NOT invoke Twilio's live API.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import twilio_service as ts  # noqa: E402


BASE = {
    "TWILIO_ACCOUNT_SID": "AC_placeholder",
    "TWILIO_AUTH_TOKEN": "tok_placeholder",
    "TWILIO_FROM_NUMBER": "+10000000000",
    "PUBLIC_BASE_URL": "https://example.test",
}


def _set(monkeypatch, mapping):
    # Clear all relevant vars first, then apply mapping.
    for k in (*BASE.keys(), "TWILIO_CONVERSATION_RELAY_WSS_URL"):
        monkeypatch.delenv(k, raising=False)
    for k, v in mapping.items():
        monkeypatch.setenv(k, v)


def test_trial_gather_valid_without_wss(monkeypatch):
    _set(monkeypatch, BASE)  # no WSS
    st = ts.transport_status(ts.TRANSPORT_TRIAL_GATHER)
    assert st["status"] == "CONFIG_VALID"
    assert st["missing"] == []


def test_conversation_relay_requires_wss(monkeypatch):
    _set(monkeypatch, BASE)  # no WSS
    st = ts.transport_status(ts.TRANSPORT_CONVERSATION_RELAY)
    assert st["status"] == "NOT_CONFIGURED"
    assert "TWILIO_CONVERSATION_RELAY_WSS_URL" in st["missing"]


def test_conversation_relay_valid_with_wss(monkeypatch):
    _set(monkeypatch, {**BASE, "TWILIO_CONVERSATION_RELAY_WSS_URL": "wss://example.test/relay"})
    st = ts.transport_status(ts.TRANSPORT_CONVERSATION_RELAY)
    assert st["status"] == "CONFIG_VALID"


@pytest.mark.parametrize(
    "missing_key",
    ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER", "PUBLIC_BASE_URL"],
)
def test_missing_base_key_marks_both_transports_not_configured(monkeypatch, missing_key):
    env = {**BASE}
    env.pop(missing_key)
    _set(monkeypatch, env)
    for transport in (ts.TRANSPORT_TRIAL_GATHER, ts.TRANSPORT_CONVERSATION_RELAY):
        st = ts.transport_status(transport)
        assert st["status"] == "NOT_CONFIGURED", (transport, st)
        assert missing_key in st["missing"]


def test_telephony_status_reports_both_transports(monkeypatch):
    _set(monkeypatch, BASE)  # trial valid, relay missing WSS
    st = ts.telephony_status()
    assert st["transports"][ts.TRANSPORT_TRIAL_GATHER]["status"] == "CONFIG_VALID"
    assert st["transports"][ts.TRANSPORT_CONVERSATION_RELAY]["status"] == "NOT_CONFIGURED"
    # Overall REAL because at least one transport is valid.
    assert st["mode"] == "REAL"


def test_telephony_status_all_empty_is_not_configured(monkeypatch):
    _set(monkeypatch, {})
    st = ts.telephony_status()
    assert st["mode"] == "NOT_CONFIGURED"
    assert st["transports"][ts.TRANSPORT_TRIAL_GATHER]["status"] == "NOT_CONFIGURED"
    assert st["transports"][ts.TRANSPORT_CONVERSATION_RELAY]["status"] == "NOT_CONFIGURED"


def test_no_secrets_in_status_output(monkeypatch):
    _set(monkeypatch, BASE)
    st = ts.telephony_status()
    # Ensure raw secret values are never surfaced in the status payload.
    import json
    blob = json.dumps(st)
    assert BASE["TWILIO_ACCOUNT_SID"] not in blob
    assert BASE["TWILIO_AUTH_TOKEN"] not in blob
    assert BASE["TWILIO_FROM_NUMBER"] not in blob
