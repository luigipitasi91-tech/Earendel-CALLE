# Certification Matrix — Future Call AI

## Release blocking rules
- False VERIFIED_SUCCESS: 0
- Guardian permission bypass: 0
- Hard-constraint bypass: 0
- Provider COMPLETED => goal success: forbidden
- Missing evidence must remain PARTIAL/UNKNOWN
- Contradicting evidence must block VERIFIED_SUCCESS
- Simulation must remain visibly labelled SIMULATED

## Core certified scenarios
1. Full explicit evidence => VERIFIED_SUCCESS
2. Date confirmed, cost missing => PARTIAL
3. No useful evidence => UNKNOWN
4. Explicit fee contradiction => FAILED
5. "Friday afternoon works" => NEUTRAL/INSUFFICIENT, never contradiction
6. Guardian blocks payment data
7. Guardian block does not itself force goal failure
8. Duplicate provider callback => idempotent
9. Out-of-order callback => no state regression
10. Incomplete transport => never verified
