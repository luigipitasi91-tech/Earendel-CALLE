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

- Local verification/regression suite included.
- Simulated scenarios are explicitly labeled `SIMULATED`.
- Higgsfield adapter is optional and cost-gated.
- Live CALL-E/Twilio certification must be completed with real credentials before claiming a live end-to-end success.

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
python -m pytest -q
```

## Submission discipline

Do not claim a live call unless the live CALL-E/Twilio path has actually been executed and evidence captured. Simulated evidence must remain clearly labeled.
