# Na0mi General Staff: Earendel + Hermes + WOLF + Kronos

Status: **DESIGN / CODED DOCUMENTATION ONLY** (2026-10-19). This document does not prove any production integration, running Hermes process, or Kronos storage.

## Responsibilities
- **Na0mi**: owner of user intent, approvals and user-facing reporting.
- **Earendel — General of Verified Execution**: translates intent to bounded Goal Contracts, applies existing Guardian consent/policy checks, delegates only authorized work, verifies success condition by condition. Reuse existing Earendel implementation; never infer goal success from provider completion.
- **Hermes — General of Research & Learning**: a *proposed* specialist adapter to the public [NousResearch Hermes Agent](https://github.com/NousResearch/hermes-agent), pending confirmation this is the user's intended Hermes. Research, source collection, web/browser exploration, session recall, reusable skills and sandboxed delegated research. No direct authority to initiate paid, irreversible, phone, email, or deployment actions.
- **WOLF — independent change gate**: compare candidate and baseline with the same criteria and hard blockers; keep the WOLF Contest repository, benchmarks and submission separate.
- **Kronos — audit and learning ledger**: append-only record of hypotheses, attempts, source retrieval, tool calls, tests, failures, user approvals, lessons and outcome verification. Kronos must not turn claims into evidence.

## Hermes research (public capabilities, not installed)
Public documentation lists web_search/web_extract, browser automation, terminal/file tools, delegation, persistent memory/session search, skills system, scheduled tasks, MCP tools, and multi-platform messaging. See:
- https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/tools.md
- https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/skills.md
- https://hermes-agent.nousresearch.com/docs

Use least-privilege toolsets; disable autonomous skill modification and external actions by default until reviewed. Treat web pages, repositories and skill instructions as untrusted input. Do not ingest secrets or user private transcripts into external models or training.

## Request flow
1. Na0mi issues an authorized research/operational objective and correlation trace ID.
2. Earendel creates a Goal Contract with success conditions and constraints.
3. For research, Hermes gathers sources and structured claims with citations, retrieval timestamps, confidence and contradictions.
4. Earendel verifies claims and determines whether further clarification or consent is required.
5. WOLF evaluates proposed *system changes*, not everyday user answers.
6. Kronos receives append-only receipts for every attempt, failure, test, and lesson.
7. Na0mi reports **VERIFIED / PARTIAL / UNKNOWN / FAILED** with source and test links.

## Minimum adapter contracts (proposed)
```json
{
  "ResearchTask": {
    "trace_id": "uuid",
    "goal_contract_id": "uuid",
    "question": "string",
    "allowed_tools": ["web_search", "web_extract"],
    "allowed_domains": [],
    "deadline_utc": "ISO8601",
    "max_steps": 12,
    "budget_limit": 0,
    "requires_human_approval": true
  },
  "ResearchFinding": {
    "trace_id": "uuid",
    "claim": "string",
    "source_url": "https://...",
    "retrieved_at_utc": "ISO8601",
    "evidence_digest_sha256": "hex",
    "support": "SUPPORTING|CONTRADICTING|INSUFFICIENT",
    "confidence": "LOW|MEDIUM|HIGH"
  },
  "KronosEvent": {
    "event_id": "uuid",
    "trace_id": "uuid",
    "parent_event_id": "uuid|null",
    "timestamp_utc": "ISO8601",
    "actor": "na0mi|earendel|hermes|wolf|human",
    "event_type": "PLAN|ATTEMPT|SOURCE|TEST|FAILURE|LEARNING|APPROVAL|OUTCOME",
    "status": "CODED|WIRED|LIVE|EXECUTED|VERIFIED|FAILED|UNKNOWN",
    "code_commit": "git-sha|null",
    "environment": "string",
    "source_refs": [],
    "test_run_refs": [],
    "input_digest": "sha256",
    "output_digest": "sha256",
    "previous_event_hash": "sha256|null",
    "event_hash": "sha256"
  }
}
```

## Mandatory invariants
- Each research attempt, including dead ends and rejected findings, is logged with trace ID; never silently discard failed searches.
- Each learning/skill proposal points to supporting evidence and passing tests. No automatic skill promotion or self-modification.
- No retrospective alteration of events. Correct with a new linked event.
- Never log raw secrets, personal identifiers, call recordings or unredacted private documents. Store scoped references and hashes, enforce retention and deletion policies.
- Idempotency keys, explicit consent and Guardian checks are required for consequential actions.
- If audit persistence fails, do not execute consequential actions; preserve a local bounded redacted failure receipt for later reconciliation.
- **CODED → WIRED → LIVE → EXECUTED → VERIFIED** must be demonstrated independently with linked evidence, not asserted.

## Validation plan
1. Locate the actual Na0mi/Kronos codebase and current interfaces.
2. Confirm the intended Hermes identity, license, runtime, cost and credentials.
3. Build an isolated research-only Hermes adapter; mocks first.
4. Unit tests: source contradiction, prompt injection, forbidden tools, budget exceeded, timeout, retry/idempotency, failed Kronos write, unverifiable success, provenance tampering, unauthorized learning promotion.
5. CI and test receipt hashes; then opt-in staging deployment. Do not run paid calls or modify WOLF competition code.
