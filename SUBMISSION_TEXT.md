# Future Call AI — CALL-E Hackathon Submission Text

## Title
Future Call AI — Evidence-First Autonomous Calling

## Tagline
Future Call AI uses CALL-E to complete real phone tasks under explicit consent, then independently verifies whether the user’s actual goal was achieved instead of trusting provider completion alone.

## Inspiration
Phone automation often treats `call completed` as success. A call can end while the user’s real objective remains unresolved, a hard constraint is violated, or evidence is missing. Future Call AI separates provider state, goal state, and verified evidence.

## What it does
A user describes a phone task in plain language. Future Call AI compiles it into a Goal Contract containing the desired outcome, hard constraints, permitted data, forbidden actions, and explicit success requirements. Guardian freezes those permissions before execution. CALL-E performs the real phone call. After the call, Earendel verifies each success requirement using terminal evidence and classifies the result as VERIFIED_SUCCESS, PARTIAL, UNKNOWN, or FAILED.

The public app includes a read-only captured production E2E proof from 13 September 2026, allowing judges to inspect a real CALL-E outcome without triggering another paid call.

## How we built it
- React frontend on Render
- Python backend on Render
- Official CALL-E Python SDK server-side
- Goal Contract and explicit consent ledger
- Guardian enforcement for allowed/forbidden data and hard constraints
- E.164 and route capability validation before provider invocation
- Background CALL-E execution with polling
- Duplicate suppression and resumable browser job state
- Requirement-level evidence verification independent from provider `completed`
- GitHub Actions for backend certification and production frontend build

## Challenges
The hardest problem was semantic reliability rather than simply making a phone ring. We handled relative dates, missing optional identity values, provider route restrictions, long-running calls, refresh/retry behavior, and duplicate paid execution. The system fails closed: uncertainty remains UNKNOWN or PARTIAL rather than being promoted to success.

## Accomplishments
- Real CALL-E production E2E completed through the deployed app
- Guardian remained ENFORCED
- Appointment move and no-additional-charge requirements independently verified
- Earendel returned VERIFIED_SUCCESS only after evidence verification
- Duplicate execution and accidental credit burn guarded at backend and browser layers
- Captured live proof can be inspected without placing another call

## What we learned
Voice-agent reliability is a state-reconciliation problem. Provider lifecycle state is useful transport evidence, but should never be treated as proof of the user’s goal. The safest architecture separates intent, permissions, provider execution, evidence, and verification.

## What’s next
Extend the same Goal Contract → Guardian → CALL-E → Evidence → Verify pipeline to service coordination, travel changes, customer support, supplier calls, and other bounded workflows where exact outcomes and permissions matter.

## Links
- App: https://future-call-ai.onrender.com
- Backend: https://earendel-calle.onrender.com
- Source: https://github.com/luigipitasi91-tech/Earendel-CALLE
