# Test Strategy

The eventual implementation must have unit, integration, and end-to-end coverage. Tests prove contract behavior; they do not prove that a specification delivers a product outcome.

| Layer | Required evidence |
| --- | --- |
| Unit | Request/result schema validation, IDs/paths, hash comparison, status mapping, artifact validation, secret redaction |
| Integration | Git workspace setup, frozen-intent copy/integrity, artifact commit, retry/idempotency, structured Conductor exchange |
| End-to-end | A fixture intent enters through a Conductor-compatible request and produces a reviewable committed `spec.md`, run record, and `spec_ready` result |
| Negative end-to-end | Missing approval, changed hash, ambiguous material requirement, invalid workspace, and unavailable dependency return safe terminal states |

Maintain deterministic fixtures for a minimal repository and intent. Validate generated artifacts structurally and review them for intent fidelity; a green test run alone cannot assert semantic correctness.
