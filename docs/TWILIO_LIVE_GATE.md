# BETA-002 LIVE Gate

This package intentionally does NOT claim a live Twilio call.

## First real controlled trial
1. Configure:
   - TWILIO_ACCOUNT_SID
   - TWILIO_AUTH_TOKEN
   - TWILIO_FROM_NUMBER
   - PUBLIC_BASE_URL
2. Use a verified destination number.
3. Start with a minimal Twilio trial flow (Say/Gather + status callbacks).
4. Validate webhook signatures.
5. Capture real transport events and real evidence.
6. Run Verify.
7. Only then may the label change from NOT_CONFIGURED to real controlled trial.

## Must remain true
`CALL_COMPLETED != TASK_COMPLETED`
