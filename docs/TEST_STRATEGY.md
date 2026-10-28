# Test Strategy

The implementation has unit, integration, and end-to-end coverage. Tests prove contract behavior; they do not prove that a specification delivers a product outcome.

| Layer | Required evidence |
| --- | --- |
| Unit | Request/result and Work Contract v3 schemas, invocation identity, path permissions, intent/profile IDs and hashes, status mapping, artifact validation, secret redaction |
| Integration | Assigned Git worktree and target commit checks, exact-byte copy of both frozen inputs, constitution/architecture inspection, artifact commit, retry/idempotency, structured Conductor exchange |
| End-to-end | A fixture invocation produces committed frozen copies, `spec.md`, Work Contract v3, run record, and a correlated `spec_ready` result with output hashes |
| Negative end-to-end | Missing freeze or snapshots, changed intent/profile hash, mismatched profile ID/version, missing acceptance criteria, material ambiguity, invalid workspace, path-scope violation, and unavailable dependency return safe terminal states |

Maintain deterministic fixtures for a minimal repository and intent. Validate generated artifacts structurally and review them for intent fidelity; a green test run alone cannot assert semantic correctness.
