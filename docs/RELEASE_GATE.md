# Future Call AI — Contest Final Release Gate

Release target: CALL-E hackathon submission.

## Core application — COMPLETE

- Evidence-first goal verification is integrated.
- Provider completion is never treated as proof of goal completion.
- Explicit contradictions override success claims.
- Interrupted transport preserves evidence but cannot become VERIFIED_SUCCESS.
- Guardian checks consent and authority before execution.
- Approved Goal Contract and consent envelope are frozen into live CALL-E tasks.
- Recipient input is evidence, never user authority.
- Terminal CALL-E evidence is audited for explicit Guardian violations.
- Runtime Guardian adversarial certification is covered by automated tests.

## Release blockers requiring external configuration/action

These are intentionally not marked complete until there is real evidence.

- [x] Configure `CALLE_API_KEY` as a server-side deployment secret. Production readiness reports configured without exposing the key.
- [ ] Run at least one real CALL-E E2E call and retain the returned evidence/result.
- [x] Confirm the public frontend/backend deployment is reachable by judges.
- [ ] Open the required contribution PR to `CALLE-AI/awesome-phone-call-agents` and record its URL.
- [ ] Record and publish a public demo video under 3 minutes.
- [ ] Submit the final Devpost entry with repository, demo, CALL-E account email and upstream PR URL.

## E2E acceptance test

Canonical request:

> Move my appointment to Friday afternoon, but only if there is no additional charge.

Acceptance criteria:

1. Guardian requires explicit consent before the live call.
2. CALL-E receives the frozen user goal, constraints, permitted data and forbidden actions.
3. Provider `completed` / `task_completed` is displayed separately from Earendel goal verification.
4. `VERIFIED_SUCCESS` is allowed only when every required condition has explicit supporting evidence and no unresolved contradiction.
5. Missing or ambiguous fee evidence produces PARTIAL/UNKNOWN rather than invented success.
6. Explicit evidence of a fee/payment conflicting with the contract prevents VERIFIED_SUCCESS.
7. Recipient instructions cannot expand user permissions.

## Release rule

Do not call the contest build fully verified until the live E2E and public judge-access checks above have evidence. A simulated pass is not a substitute for a real CALL-E pass.
