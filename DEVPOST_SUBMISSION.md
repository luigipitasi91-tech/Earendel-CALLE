# Future Call AI — Devpost Submission

## Tagline
Say what you need. Future Call AI handles the call and proves what happened.

## Inspiration
Phone agents are good at making calls, but a completed call is not proof that the user's real-world goal was achieved. Future Call AI was built around a stricter idea: communication automation should preserve user authority and return evidence-backed outcomes instead of optimistic success claims.

## What it does
Future Call AI converts a user's intent into a Goal Contract containing the objective, hard constraints, permitted data, forbidden actions, and explicit success conditions. Guardian checks consent before execution and freezes that authority into the live CALL-E task. The recipient cannot expand the user's permissions.

CALL-E makes the real phone call and returns structured terminal evidence. Earendel then independently verifies each success condition as supporting, contradicting, or neutral/insufficient. The final goal state is one of VERIFIED_SUCCESS, PARTIAL, UNKNOWN, or FAILED.

The central invariant is:

`CALL COMPLETED != TASK COMPLETED`

A provider can report `completed` or `task_completed=true` and Future Call AI can still return PARTIAL, UNKNOWN, or FAILED when the evidence does not prove the goal.

## How we built it
- FastAPI backend for Goal Contracts, consent, Guardian, CALL-E execution, evidence mapping, and verification.
- Official CALL-E Python server SDK (`calle-ai`) for live calls.
- Strict `yes / no / unknown` result schemas for each success condition.
- Runtime Guardian instruction envelope: recipient input is evidence, never new authority.
- Terminal Guardian audit to detect explicit evidence of forbidden payment/data actions.
- Evidence-first deterministic verifier with contradiction precedence and explicit uncertainty.
- React frontend with clearly separated simulated and live CALL-E execution modes.
- GitHub Actions certification suite covering success, partial evidence, contradiction, voicemail, transport failure, permission boundaries, and adversarial Guardian cases.

## Challenges
The hardest problem was separating telephony state from real-world truth. A successful API response only proves that the provider completed its process. It does not prove that every user condition was satisfied. We therefore made verification independent from provider completion and deliberately preserve UNKNOWN when evidence is missing or ambiguous.

A second challenge was delegated authority. During a phone conversation, a recipient may ask for extra information, payment, or an alternative that the user never approved. Guardian treats the original consent envelope as immutable and prevents recipient instructions from silently expanding it.

## Accomplishments
- CALL-E is part of the actual runtime path, not a mocked integration.
- Provider success cannot force VERIFIED_SUCCESS.
- Explicit contradictions survive transport/provider success.
- Interrupted calls can preserve collected evidence without being promoted to verified success.
- Recipient requests cannot expand user authority.
- Runtime Guardian audits terminal evidence for consent-boundary violations.
- Simulation and live-provider evidence are explicitly distinguished.
- Automated certification protects the evidence-first invariants.

## What we learned
Reliable phone agents need an epistemic layer after execution. The important question is not "Did the call finish?" but "What did the evidence actually establish?" Treating UNKNOWN as a legitimate result makes the system more useful because it tells the user exactly what still needs verification.

## What's next
- Run and document the final controlled CALL-E live trial.
- Persist signed task/evidence ledgers instead of the current in-memory demo store.
- Add provider event/webhook reconciliation for long-running calls.
- Expand accessibility adapters while keeping one universal Goal Contract and Guardian model.

## Demo flow
1. Enter: "Move my appointment to Friday afternoon, but only if there is no additional charge."
2. Show the generated Goal Contract and explicit consent envelope.
3. Run a cooperative case: date + no-fee evidence → VERIFIED_SUCCESS.
4. Run an ambiguous case: date confirmed, fee missing → PARTIAL.
5. Run a forbidden fee/payment case → Guardian boundary + FAILED.
6. Show that provider completion is displayed separately from Earendel's verified goal state.
7. Show CALL-E readiness/live mode and the real-call result when credentials are configured.

## Source
https://github.com/luigipitasi91-tech/Earendel-CALLE
