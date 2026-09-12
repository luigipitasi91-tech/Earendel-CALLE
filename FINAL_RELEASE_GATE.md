# Future Call AI — Final Release Gate

## GREEN — completed in repository
- Public contest repository exists.
- Official CALL-E runtime integration exists server-side.
- Evidence-first verifier is merged to `main`.
- Runtime Guardian is merged to `main`.
- Recipient input cannot expand the consent envelope.
- Provider `completed` / `task_completed` cannot force VERIFIED_SUCCESS.
- Adversarial Guardian tests are certified.
- Pre-merge Runtime Guardian certification passed (GitHub Actions run 15).
- Devpost narrative and demo flow are prepared.
- Docker/backend/frontend scaffolding exists.

## EXTERNAL GATES — cannot be truthfully marked complete without external credentials/actions
1. Configure `CALLE_API_KEY` as a server-side secret. Never put it in browser code, screenshots, GitHub, or chat.
2. Run at least one controlled real CALL-E E2E call and retain call ID + terminal evidence.
3. Deploy a public testing URL or provide another judge-accessible test build.
4. Record and publish a public demo video under 3 minutes.
5. Open the required contribution PR to `CALLE-AI/awesome-phone-call-agents` and save its URL.
6. Complete the Devpost form, including CALL-E account email and contribution PR URL.

## Release policy
Do not claim a real CALL-E call happened until a real provider call ID and evidence are captured.
Do not claim a public deployment exists until its URL is reachable.
Do not claim submission is complete until Devpost confirms it.

## Deadline
Current official Devpost rules/overview show September 14, 2026 at 11:45 PM SGT. Finish external gates before that time.
