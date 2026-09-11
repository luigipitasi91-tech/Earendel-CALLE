# CALL-E Runtime Integration

Future Call AI uses the official Python server SDK:

```bash
pip install calle-ai==0.7.0
```

The API key stays server-side in `CALLE_API_KEY`.

## Runtime path

`POST /calls/calle/live`

1. Load the Earendel task and Goal Contract.
2. Require explicit recorded user consent.
3. Run Guardian before any external action.
4. Validate recipient phone number as E.164.
5. Build a strict CALL-E `result_schema` from the Goal Contract success conditions.
6. Invoke `CalleClient.calls.create_and_wait(...)`.
7. Map CALL-E terminal structured result into SUPPORTING / CONTRADICTING / NEUTRAL_OR_INSUFFICIENT evidence.
8. Run Earendel Verify.
9. Return provider state and goal state separately.

## Evidence discipline

CALL-E `task_completed` is useful provider evidence but does **not** directly set Earendel to `VERIFIED_SUCCESS`.

Each mandatory success condition must independently survive verification. Unknown/ambiguous evidence remains `unknown`, producing PARTIAL or UNKNOWN rather than an invented success.

## Live gate

The integration is code-complete and locally tested with a deterministic injected client. A real live call is still required before the submission can claim end-to-end live certification.
