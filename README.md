# Earendel / Future Call AI — CALL-E Submission

Evidence-first autonomous calling with explicit consent, bounded permissions, Guardian enforcement, and post-call verification.

## Core principle

**Provider state ≠ goal state ≠ verified evidence.**

A telephony provider reporting `completed` is not enough. The system only marks the user goal as verified when every required success condition has explicit supporting evidence and no surviving contradiction.

## Vertical slice

1. User expresses a phone task in plain language.
2. The request is compiled into a Goal Contract.
3. Guardian enforces consent, allowed data, forbidden data, and hard constraints.
4. CALL-E performs the call.
5. Transcript/events are collected.
6. Verify evaluates each success condition.
7. Result is classified as VERIFIED SUCCESS / PARTIAL / UNKNOWN / FAILED.
8. Evidence is shown condition-by-condition.

## Safety / consent model

- Explicit user authorization before execution.
- Recipients cannot expand permissions.
- Forbidden data cannot be disclosed.
- Paid alternatives cannot be accepted without new consent.
- Guardian events are separated from outcome verification.
- Creative tools such as Higgsfield are optional adapters and are not part of the trust boundary.

## Current status

- **150/150 backend certification tests pass.**
- GitHub Actions certifies both the backend suite and the frontend production build.
- Official CALL-E Python SDK integration is present server-side via `calle-ai==0.7.0`.
- Live runtime uses `CalleClient.calls.create_and_wait(...)` behind Guardian + explicit consent.
- CALL-E terminal structured results are mapped into SUPPORTING / CONTRADICTING / NEUTRAL_OR_INSUFFICIENT evidence before Earendel Verify runs.
- Simulated scenarios are explicitly labeled `SIMULATED`; the UI now separates Simulated and Real CALL-E execution modes.
- Higgsfield remains optional, cost-gated, and outside the Guardian/Verify trust boundary.
- Public frontend: https://future-call-ai.onrender.com
- Public backend: https://earendel-calle.onrender.com
- Frontend → backend → CALL-E credential readiness and provider rejection diagnostics are verified in production.
- A real successful CALL-E call is still pending; no live end-to-end success is claimed yet.

## Repository layout

- `backend/` — verification, Guardian integration, telephony/readiness, tests.
- `docs/` — architecture and adapter notes.
- `TEST_REPORT.txt` — latest local suite result.
- `SUBMISSION_CHECKLIST.md` — final CALL-E/Devpost readiness checklist.
- `DEMO_SCRIPT.md` — <3 minute demo plan.
- `ARCHITECTURE.md` — concise system architecture.

## Run tests

```bash
cd backend
PYTHONPATH=. pytest -q
```

Latest local result: **150 passed**. The same suite is required by GitHub Actions.

## CALL-E configuration

Set the API key only on the backend/server:

```bash
export CALLE_API_KEY="..."
```

Optional:

```bash
export CALLE_BASE_URL="https://api.heycall-e.com"
```

The browser never receives the CALL-E API key. Live execution uses `POST /calls/calle/start`, then polls `GET /calls/calle/status/{job_id}` so a long provider call does not hold a browser request open.

Before a job is created, the backend validates the selected route and resolves the E.164 number to its actual destination region. The known-rejected `GB/en-GB` route is blocked before CALL-E receives a request. The controlled demo currently exposes only the SDK-documented `US/en-US` route; published coverage is never presented as a runtime guarantee.

## Submission discipline

Do not claim a live call unless the live CALL-E/Twilio path has actually been executed and evidence captured. Simulated evidence must remain clearly labeled.
