# CALL-E Runtime Integration

Future Call AI uses the official Python server SDK:

```bash
pip install calle-ai==0.7.0
```

The API key stays server-side in `CALLE_API_KEY`.

## Runtime path

`POST /calls/calle/start` followed by `GET /calls/calle/status/{job_id}`

1. Load the Earendel task and Goal Contract.
2. Require explicit recorded user consent.
3. Run Guardian before any external action.
4. Validate the route and resolve the E.164 number to its actual destination region before creating a provider job.
5. Reject known unavailable or uncertified region/language combinations without consuming a CALL-E call.
6. Build a strict CALL-E `result_schema` from the Goal Contract success conditions.
7. Run `CalleClient.calls.create_and_wait(...)` in a background job while the browser polls Earendel.
8. Map CALL-E terminal structured result into SUPPORTING / CONTRADICTING / NEUTRAL_OR_INSUFFICIENT evidence.
9. Run Earendel Verify.
10. Return provider state and goal state separately.

## Evidence discipline

CALL-E `task_completed` is useful provider evidence but does **not** directly set Earendel to `VERIFIED_SUCCESS`.

Each mandatory success condition must independently survive verification. Unknown/ambiguous evidence remains `unknown`, producing PARTIAL or UNKNOWN rather than an invented success.

## Live gate

The integration, public deployment, credential readiness, capability gate, background polling, and provider diagnostics are verified. A real successful CALL-E call is still required before the submission can claim end-to-end live certification.
