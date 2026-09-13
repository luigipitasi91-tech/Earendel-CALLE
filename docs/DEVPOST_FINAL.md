# Devpost Final Copy — Future Call AI

## Project name
Future Call AI — Evidence-First Autonomous Calling

## One-line pitch
Say what you need. Future Call AI handles the call within your permission and proves what actually happened.

## Inspiration
Phone calls remain a barrier for people who cannot, do not want to, or struggle to communicate synchronously. Existing voice agents can place calls, but a completed call is not proof that the user's real-world goal was completed correctly. Future Call AI was built around a stricter idea: communication should end in an evidence-backed outcome, not an AI success claim.

## What it does
The user states a goal and constraints. Future Call AI converts them into a Goal Contract, obtains explicit consent, freezes the permitted authority into the CALL-E task, executes the call, maps the returned evidence to each success condition, attempts to refute success, and returns VERIFIED_SUCCESS, PARTIAL, UNKNOWN, or FAILED.

A provider reporting `completed` or `task_completed=true` never overrides Earendel verification.

## How we built it
The application uses a React frontend and a FastAPI backend. CALL-E is integrated server-side through its Python SDK. The Guardian layer checks consent and authority before execution and embeds the approved Goal Contract, allowed data, hard constraints, and forbidden actions into the live CALL-E instruction. Returned structured results and evidence are then independently evaluated by Earendel's deterministic verifier.

The runtime also audits terminal evidence for explicit consent-boundary violations. Recipient statements are treated as evidence, not as authority to change the user's permissions.

## Key architecture
INTENT → GOAL CONTRACT → GUARDIAN → CALL-E → EVIDENCE → VERIFY → RESULT

Core invariant: CALL COMPLETED != TASK VERIFIED.

## Challenges
The hardest problem was separating telephony success from real-world goal success. A call can finish successfully while the requested outcome remains ambiguous, partially achieved, or violates a constraint. We therefore designed the verifier to fail closed: ambiguity stays UNKNOWN/PARTIAL, contradictions block verified success, and incomplete transport cannot be promoted to VERIFIED_SUCCESS.

A second challenge was enforcing user authority when recipient conversation can introduce new requests. Future Call AI freezes the user's permission envelope and treats recipient input only as evidence.

## Accomplishments
- Direct CALL-E SDK integration.
- Evidence-first deterministic verification.
- Explicit consent and Guardian enforcement.
- Runtime consent-boundary audit.
- Adversarial certification tests covering false-success and permission-expansion cases.
- Accessible barrier-first interaction model.

## What we learned
The important distinction is not whether an AI can make a phone call. It is whether the system can prove what happened without overstating certainty or silently expanding authority. UNKNOWN is therefore a valid product result, not an error to hide.

## What's next
Expand evidence provenance and chronology-aware contradiction resolution, add more communication channels behind the same consent/verification model, and develop reusable verified-call workflows while preserving the same Guardian boundaries.

## Demo sequence
1. Enter: “Move my appointment to Friday afternoon, but only if there is no additional charge.”
2. Show the generated Goal Contract and explicit consent.
3. Show Guardian approval and live CALL-E execution.
4. Show provider state separately from goal state.
5. Show evidence for date and fee conditions.
6. Show Earendel's final verification.
7. Demonstrate a failure/ambiguity case where provider completion does not become VERIFIED_SUCCESS.

## Final fields to insert after external release actions
- Public repository: https://github.com/luigipitasi91-tech/Earendel-CALLE
- Public demo URL: https://future-call-ai.onrender.com
- Demo video URL: PENDING RECORDING
- CALL-E awesome repository PR URL: PENDING UPSTREAM PR
- CALL-E account email: luigipitasi91@gmail.com (confirm before submission)
