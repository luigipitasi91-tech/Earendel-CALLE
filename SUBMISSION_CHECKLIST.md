# CALL-E Submission Checklist

## Code / runtime
- [x] CALL-E is invoked at runtime, not merely mentioned.
- [x] Live call credentials are configured safely.
- [ ] One real end-to-end call is completed.
- [ ] Transcript and evidence are captured.
- [x] Guardian blocks forbidden-data disclosure.
- [x] Verification never equates provider `completed` with goal success.
- [x] Simulated and live evidence are visually distinguishable.

## Certification scenarios
- [x] Cooperative recipient → VERIFIED SUCCESS
- [x] Fee required / hard constraint violated → FAILED
- [x] Rescheduled but fee not confirmed → PARTIAL
- [x] Voicemail → UNKNOWN
- [x] Forbidden data request → Guardian blocks
- [x] Telephony failure → FAILED
- [ ] Real CALL-E live call → evidence captured
- [x] Live provider rejection is surfaced and blocked routes cannot be retried blindly

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
