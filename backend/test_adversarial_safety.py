import unittest
from adversarial_safety import Evidence, adjudicate, retry_decision


class AdversarialSafetyTests(unittest.TestCase):
    def test_conflicting_authenticated_sources_fail_closed(self):
        evidence = [
            Evidence("transcript", "call1", "+15551234567", "appointment", "SUPPORTING", True),
            Evidence("provider_record", "call1", "+15551234567", "appointment", "CONTRADICTING", True),
        ]
        result = adjudicate(["appointment"], evidence, call_id="call1", recipient="+15551234567")
        self.assertEqual(result["verdict"], "NEEDS_HUMAN")

    def test_wrong_recipient_never_verified(self):
        evidence = [Evidence("provider", "call1", "+15550000000", "appointment", "SUPPORTING", True)]
        result = adjudicate(["appointment"], evidence, call_id="call1", recipient="+15551234567")
        self.assertEqual(result["verdict"], "NEEDS_HUMAN")

    def test_unsigned_evidence_is_insufficient(self):
        evidence = [Evidence("webhook", "call1", "+15551234567", "appointment", "SUPPORTING", False)]
        result = adjudicate(["appointment"], evidence, call_id="call1", recipient="+15551234567")
        self.assertEqual(result["verdict"], "UNKNOWN")

    def test_all_authenticated_conditions(self):
        evidence = [Evidence("provider", "call1", "+15551234567", x, "SUPPORTING", True) for x in ("appointment", "price")]
        result = adjudicate(["appointment", "price"], evidence, call_id="call1", recipient="+15551234567")
        self.assertEqual(result["verdict"], "VERIFIED_SUCCESS")

    def test_timeout_without_lookup_never_retries(self):
        self.assertEqual(retry_decision(idempotency_key="k", persisted_job=None, provider_state="timeout", lookup_confirmed=False), "BLOCK_UNKNOWN_PROVIDER_STATE")

    def test_resume_same_job(self):
        self.assertEqual(retry_decision(idempotency_key="k", persisted_job="job1", provider_state="timeout", lookup_confirmed=False), "RESUME_EXISTING_JOB")

    def test_completed_call_not_retried(self):
        self.assertEqual(retry_decision(idempotency_key="k", persisted_job=None, provider_state="completed", lookup_confirmed=True), "BLOCK_POSSIBLE_DUPLICATE")

    def test_missing_idempotency_key(self):
        self.assertEqual(retry_decision(idempotency_key="", persisted_job=None, provider_state="failed", lookup_confirmed=True), "BLOCK_MISSING_IDEMPOTENCY_KEY")


if __name__ == "__main__":
    unittest.main()
