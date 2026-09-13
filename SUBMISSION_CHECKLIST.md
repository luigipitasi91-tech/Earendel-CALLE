# CALL-E Submission Checklist

## Code / runtime
- [x] CALL-E is invoked at runtime, not merely mentioned.
- [x] Live call credentials are configured safely.
- [x] One real end-to-end call is completed.
- [x] Live requirement-level evidence is captured.
- [x] Guardian blocks forbidden-data disclosure.
- [x] Verification never equates provider `completed` with goal success.
- [x] Simulated and live evidence are visually distinguishable.
- [x] Relative weekday ambiguity is resolved before provider execution.
- [x] Duplicate live provider execution is suppressed.
- [x] Long-running browser jobs resume the same CALL-E job instead of starting another call.
- [x] Missing optional permitted data is never invented.

## Certification scenarios
- [x] Cooperative recipient → VERIFIED SUCCESS
- [x] Fee required / hard constraint violated → FAILED
- [x] Rescheduled but fee not confirmed → PARTIAL
- [x] Voicemail → UNKNOWN
- [x] Forbidden data request → Guardian blocks
- [x] Telephony failure → FAILED
- [x] Real CALL-E live call → VERIFIED_SUCCESS evidence captured
- [x] Live provider rejection is surfaced and blocked routes cannot be retried blindly
- [x] Duplicate request → provider execution suppressed / existing job reused

## Verified production E2E — 13 Sep 2026
- [x] Provider state `completed`
- [x] Guardian `ENFORCED`
- [x] Appointment condition verified
- [x] No-additional-charge condition verified
- [x] Earendel state `VERIFIED_SUCCESS`
- [x] Evidence retained without exposing CALL-E API credentials

## Credit discipline
- [x] Simulated mode uses no CALL-E credits.
- [x] UI explicitly warns that live mode consumes credits.
- [x] One active live job at a time.
- [x] Do not repeat the captured live E2E just for rehearsal; use Simulated mode.

## Devpost
- [x] Public demo/build URL
- [ ] Public demo video under 3 minutes
- [x] English project description
- [x] Architecture explanation
- [x] Testing instructions
- [x] CALL-E runtime use explained clearly
- [ ] Pull request opened to required CALL-E repository
- [ ] PR URL added to Devpost
- [ ] Final submission reviewed before deadline
