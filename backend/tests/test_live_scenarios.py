"""Live end-to-end tests against REACT_APP_BACKEND_URL for iteration 4.

Verifies:
- /api/telephony/status per-transport structure and NOT_CONFIGURED state
- Frozen SIMULATED regression: 6 scenarios produce exact goal_state
- REAL mode returns 400 NOT_CONFIGURED with missing keys listed (no real credentials)
- No credentials appear in any response body
"""
import os
import re
import json
import requests

BASE = "https://evidence-first-27.preview.emergentagent.com/api"

REQUEST_TEXT = "Move my appointment to Friday afternoon, but only if there is no additional charge."


def test_telephony_status_shape():
    r = requests.get(f"{BASE}/telephony/status", timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "transports" in data, data
    tg = data["transports"]["TWILIO_TRIAL_GATHER"]
    cr = data["transports"]["TWILIO_CONVERSATION_RELAY"]
    assert "status" in tg and "missing" in tg
    assert "status" in cr and "missing" in cr
    assert tg["status"] == "NOT_CONFIGURED"
    assert cr["status"] == "NOT_CONFIGURED"
    assert len(tg["missing"]) > 0
    assert len(cr["missing"]) > 0
    # No credentials leaked
    body = r.text
    assert "TWILIO_AUTH_TOKEN=" not in body
    print("telephony/status OK:", json.dumps(data, indent=2))


def _create_contract_with_consent():
    r = requests.post(f"{BASE}/contracts", json={"request_text": REQUEST_TEXT}, timeout=90)
    assert r.status_code == 200, r.text
    cid = r.json()["id"]
    r2 = requests.post(f"{BASE}/contracts/{cid}/consent", json={"granted": True}, timeout=30)
    assert r2.status_code == 200, r2.text
    return cid


EXPECTED = {
    "cooperative": ("VERIFIED_SUCCESS", 0),
    "extra_fee": ("FAILED", None),
    "no_charge_unclear": ("PARTIAL", None),
    "voicemail": ("UNKNOWN", None),
    "forbidden_probe": ("VERIFIED_SUCCESS", 1),
    "provider_failed": ("FAILED", None),
}


def test_frozen_simulated_regression():
    results = {}
    for scenario, (expected_state, expected_blocks) in EXPECTED.items():
        cid = _create_contract_with_consent()
        r = requests.post(
            f"{BASE}/contracts/{cid}/execute",
            json={"mode": "SIMULATED", "scenario": scenario},
            timeout=120,
        )
        assert r.status_code == 200, f"{scenario}: {r.status_code} {r.text}"
        data = r.json()
        gs = data.get("goal_state")
        gb = data.get("guardian_blocks") or []
        results[scenario] = (gs, len(gb))
        assert gs == expected_state, f"{scenario}: expected {expected_state}, got {gs}. Full: {data}"
        if expected_blocks is not None:
            assert len(gb) == expected_blocks, f"{scenario}: expected {expected_blocks} blocks, got {len(gb)}"
    print("Frozen regression PASS:", results)


def test_real_mode_trial_gather_not_configured():
    cid = _create_contract_with_consent()
    r = requests.post(
        f"{BASE}/contracts/{cid}/execute",
        json={"mode": "REAL", "transport": "TWILIO_TRIAL_GATHER", "recipient_number": "+15551234567"},
        timeout=30,
    )
    assert r.status_code == 400, r.text
    body = r.text
    assert "NOT_CONFIGURED" in body
    # Should list at least one missing env key
    assert "TWILIO" in body or "PUBLIC_BASE_URL" in body
    print("REAL trial_gather 400:", body)


def test_real_mode_conversation_relay_not_configured():
    cid = _create_contract_with_consent()
    r = requests.post(
        f"{BASE}/contracts/{cid}/execute",
        json={"mode": "REAL", "transport": "TWILIO_CONVERSATION_RELAY", "recipient_number": "+15551234567"},
        timeout=30,
    )
    assert r.status_code == 400, r.text
    assert "TWILIO_CONVERSATION_RELAY_WSS_URL" in r.text, r.text
    print("REAL conversation_relay 400:", r.text)


def test_no_credentials_echoed_anywhere():
    # Even though env is empty, ensure endpoint responses never include env-var-value patterns
    endpoints = [f"{BASE}/telephony/status", f"{BASE}/simulator/scenarios", f"{BASE}/"]
    for u in endpoints:
        r = requests.get(u, timeout=30)
        assert r.status_code == 200
        body = r.text
        # Look for likely leaked keys like AC... (Twilio SID) or long secrets
        assert not re.search(r"\bAC[a-f0-9]{32}\b", body), f"Twilio SID leaked at {u}"
        # env-var NAMES in 'missing' list are fine; assert no VALUES leak
        assert "sk-emergent-" not in body, f"LLM key leaked at {u}"


if __name__ == "__main__":
    test_telephony_status_shape()
    test_frozen_simulated_regression()
    test_real_mode_trial_gather_not_configured()
    test_real_mode_conversation_relay_not_configured()
    test_no_credentials_echoed_anywhere()
    print("ALL LIVE TESTS PASSED")
