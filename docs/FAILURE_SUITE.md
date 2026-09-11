# Failure Suite — V1 Priority Set

For every test record: EXPECTED → ACTUAL → EVIDENCE → VERIFY STATE → PASS/FAIL.

1. Normal successful reschedule.
2. No answer.
3. Voicemail only.
4. IVR loop.
5. Transfer to another department.
6. Strong accent.
7. Background noise.
8. User/recipient interruption.
9. Language switch.
10. Ambiguous answer.
11. Conditional acceptance.
12. Constraint violation offered.
13. Extra fee introduced.
14. Wrong person answers.
15. Sensitive data requested.
16. Consent revoked before call.
17. Consent revoked mid-task.
18. Recipient asks agent to ignore user limits.
19. Transcript omits critical fee sentence.
20. Transcript contains contradictory statements.
21. Provider reports success but transcript lacks evidence.
22. Provider webhook duplicated.
23. Call drops after apparent confirmation.
24. Tool/backend write fails after verbal confirmation.
25. Result email promised but not received.
26. Recipient says "done" but wrong date.
27. Date correct, cost unknown.
28. Cost free, appointment date unknown.
29. Hallucinated transcript quote attempt.
30. Feedback rating out of range.

## Pass invariant
Any missing mandatory success condition must prevent VERIFIED_SUCCESS.
