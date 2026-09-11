# CALL-E Submission Checklist

## Code / runtime
- [ ] CALL-E is invoked at runtime, not merely mentioned.
- [ ] Live call credentials are configured safely.
- [ ] One real end-to-end call is completed.
- [ ] Transcript and evidence are captured.
- [ ] Guardian blocks forbidden-data disclosure.
- [ ] Verification never equates provider `completed` with goal success.
- [ ] Simulated and live evidence are visually distinguishable.

## Certification scenarios
- [x] Cooperative recipient → VERIFIED SUCCESS
- [x] Fee required / hard constraint violated → FAILED
- [x] Rescheduled but fee not confirmed → PARTIAL
- [x] Voicemail → UNKNOWN
- [x] Forbidden data request → Guardian blocks
- [x] Telephony failure → FAILED
- [ ] Real CALL-E live call → evidence captured
- [ ] Live failure/retry path checked

## Devpost
- [ ] Public demo/build URL
- [ ] Public demo video under 3 minutes
- [ ] English project description
- [ ] Architecture explanation
- [ ] Testing instructions
- [ ] CALL-E runtime use explained clearly
- [ ] Pull request opened to required CALL-E repository
- [ ] PR URL added to Devpost
- [ ] Final submission reviewed before deadline
