# Architecture

## Trust boundary

User Intent
→ Goal Contract
→ Guardian + Consent
→ CALL-E / Telephony
→ Transcript + Provider Events
→ Verify
→ Evidence-backed Result

## Separation of concerns

### Goal Contract
Defines:
- goal
- preferred outcome
- hard constraints
- permitted data
- forbidden data
- forbidden actions
- explicit success conditions

### Guardian
Prevents execution or disclosure outside the contract. Guardian blocks are logged but are not themselves treated as evidence that the business goal failed.

### Telephony / CALL-E
Performs the real-world interaction. Provider state is transport state only.

### Verify
Evaluates each requirement using:
- SUPPORTING
- CONTRADICTING
- NEUTRAL_OR_INSUFFICIENT

A final success requires all mandatory conditions to be supported after refutation attempts.

### Creative Adapter
Higgsfield is optional, isolated, budget-gated, and cannot affect Guardian/Verify/CALL-E availability.
