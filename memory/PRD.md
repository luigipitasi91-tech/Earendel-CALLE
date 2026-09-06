# Future Call AI — PRD

## Original problem statement
Build a mobile-first web app "Future Call AI" that turns a natural-language phone
task into a Goal Contract, gates execution with a Guardian consent layer,
performs a real Twilio Programmable Voice + ConversationRelay call when
configured, collects evidence, and independently verifies whether the user's
goal was achieved. Core invariants: call completed ≠ task completed; AI claim ≠
verified evidence; provider success ≠ user goal success. Never display success
unless every required condition has explicit supporting evidence.

## User personas
- Individual who wants an assistant to make a low-risk phone task on their
  behalf (rescheduling, cancelling, simple inquiries) with proof.

## Core requirements (static)
Vertical slice: REQUEST → GOAL CONTRACT → GUARDIAN → CALL → EVIDENCE → VERIFY →
RESULT. Deterministic Verify Engine. Guardian invariants strictly enforced.
Twilio boundary (TwiML, ConversationRelay WS, HTTP + WS signature validation,
idempotent status callbacks) present in code; SIMULATED path clearly labeled.

## Implemented (2026-02)
- Backend FastAPI with `/api/contracts`, `/api/contracts/{id}/consent`,
  `/api/contracts/{id}/revoke`, `/api/contracts/{id}/execute`, `/api/calls/{id}`,
  `/api/calls/{id}/verify`, `/api/twilio/voice`, `/api/twilio/status`, WS
  `/api/twilio/relay`, `/api/telephony/status`, `/api/simulator/scenarios`.
- Claude Sonnet 4.6 (Emergent Universal Key) extracts Goal Contract; deterministic
  fallback for the demo request. Verify Engine is fully deterministic.
- 6 SIMULATED scenarios (cooperative, extra_fee, no_charge_unclear, voicemail,
  forbidden_probe, provider_failed).
- Idempotent Twilio status callback (dedup by CallSid+SequenceNumber+CallStatus)
  with out-of-order tolerance; X-Twilio-Signature validation on HTTP + WS
  handshake.
- 11 deterministic invariant tests — all pass.
- Mobile-first React UI: Request → Contract → Guardian → Result with distinct
  visual verdict states (VERIFIED SUCCESS, PARTIAL, UNKNOWN, FAILED) and mode
  badges (REAL / SIMULATED / NOT CONFIGURED).

## Status
- REAL Twilio: NOT_CONFIGURED (env vars empty).
- SIMULATED path: fully working, always labeled SIMULATED.
- LLM: Emergent Universal Key configured; goal extraction verified with Claude
  Sonnet 4.6.

## Backlog (P0/P1/P2)
- P1: Live call screen (real-time streaming transcript, emergency revoke).
- P1: Persist and browse past call runs (Call History drawer).
- P2: Editable Goal Contract inline before consent.
- P2: Server-Sent-Events endpoint for streaming transcript to the UI in REAL mode.
- P2: Contract signing with a hash to prove no post-hoc edits.

## Next steps to first REAL Twilio call
1. Populate `/app/backend/.env`:
   `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`,
   `PUBLIC_BASE_URL` (the externally reachable https base for this app),
   `TWILIO_CONVERSATION_RELAY_WSS_URL` (wss:// URL to /api/twilio/relay).
2. `sudo supervisorctl restart backend`.
3. Verify `GET /api/telephony/status` returns `mode:"REAL"` and `signature_validation:"ENABLED"`.
4. Trigger a call with `POST /api/contracts/{cid}/execute {mode:"REAL", recipient_number:"+1..."}` after granting consent.
