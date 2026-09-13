# Earendel / Future Call AI — CALL-E Submission

Evidence-first autonomous calling with explicit consent, bounded permissions, Guardian enforcement, and post-call verification.

## Core principle

**Provider state ≠ goal state ≠ verified evidence.**

A telephony provider reporting `completed` is not enough. The system only marks the user goal as verified when every required success condition has explicit supporting evidence and no surviving contradiction.

## Vertical slice

1. User expresses a phone task in plain language.
2. The request is compiled into a Goal Contract.
3. Guardian enforces consent, allowed data, forbidden data, and hard constraints.
4. Relative dates such as `Friday` are resolved before provider execution.
5. CALL-E performs the call.
6. Transcript/events are collected.
7. Verify evaluates each success condition.
8. Result is classified as VERIFIED SUCCESS / PARTIAL / UNKNOWN / FAILED.
9. Evidence is shown condition-by-condition.

## Safety / consent model

- Explicit user authorization before execution.
- Recipients cannot expand permissions.
- Forbidden data cannot be disclosed.
- Paid alternatives cannot be accepted without new consent.
- Missing permitted identity data is never invented.
- Guardian events are separated from outcome verification.
- Creative tools such as Higgsfield are optional adapters and are not part of the trust boundary.

## Live CALL-E reliability

- Live execution uses the official CALL-E Python SDK server-side via `CalleClient.calls.create_and_wait(...)`.
- Duplicate live provider requests are suppressed with a stable idempotency key plus a backend duplicate window.
- The browser saves the active CALL-E job and resumes polling the same job after timeout or refresh instead of creating another call.
- Simulated mode never places a real call or uses CALL-E credits.
- Live mode is explicitly labeled as credit-consuming and allows only one active job at a time.
- The browser never receives the CALL-E API key.

## Verified live E2E evidence

On **13 September 2026**, a controlled live CALL-E test completed end-to-end through the production frontend/backend path.

Observed result:
- CALL-E provider state: `completed`
- provider task completed: `true`
- Guardian: `ENFORCED`
- appointment condition: verified
- no-additional-charge condition: verified
- Earendel final goal state: `VERIFIED_SUCCESS`
- provider call id: `call_4fEkmGdrngWlQz4uT7H_yg`

The system did not infer success from provider completion alone; the final verdict was produced only after requirement-level evidence verification.

## Current status

- GitHub Actions certifies the backend suite and frontend production build.
- Official CALL-E Python SDK integration is present server-side via `calle-ai==0.7.0`.
- CALL-E terminal structured results are mapped into SUPPORTING / CONTRADICTING / NEUTRAL_OR_INSUFFICIENT evidence before Earendel Verify runs.
- Simulated scenarios are explicitly labeled `SIMULATED`; the UI separates Simulated and Real CALL-E execution modes.
- Known-rejected routes are blocked before provider invocation.
- Relative weekday ambiguity, missing optional identity data, duplicate execution, and long-running job resume behavior are hardened.
- Higgsfield remains optional, cost-gated, and outside the Guardian/Verify trust boundary.
- Public frontend: https://future-call-ai.onrender.com
- Public backend: https://earendel-calle.onrender.com

## Repository layout

- `backend/` — verification, Guardian integration, CALL-E adapter, readiness and tests.
- `frontend/` — Goal Contract / Guardian / live-call / evidence UI.
- `docs/` — architecture and adapter notes.
- `TEST_REPORT.txt` — certification snapshot.
- `SUBMISSION_CHECKLIST.md` — final submission readiness checklist.
- `DEMO_SCRIPT.md` — <3 minute demo plan.
- `ARCHITECTURE.md` — concise system architecture.

## Run tests

```bash
cd backend
PYTHONPATH=. pytest -q
```

The same backend suite plus the frontend production build are required by GitHub Actions.

## CALL-E configuration

Set the API key only on the backend/server:

```bash
export CALLE_API_KEY="..."
```

Optional:

```bash
export CALLE_BASE_URL="https://api.heycall-e.com"
```

Live execution uses `POST /calls/calle/start`, then polls `GET /calls/calle/status/{job_id}` so a long provider call does not hold a browser request open. The frontend persists the current job id in session storage and resumes it rather than starting a duplicate call.

Before a job is created, the backend validates the selected route and resolves the E.164 number to its actual destination region. The known-rejected `GB/en-GB` route is blocked before CALL-E receives a request. The controlled demo currently exposes only the SDK-documented `US/en-US` route; published coverage is never presented as a runtime guarantee.

## Submission discipline

The verified live result above is the captured E2E proof. **Do not burn additional CALL-E credits merely to re-prove it.** Use Simulated mode for repeated demo rehearsals and only place another live call when deliberately authorized.
