# Build Instructions

## Objective

Build a stateless Spec & Design Agent that consumes a frozen product intent and produces a versioned, reviewable specification. It is the first engineering-stage worker after **Ready for Planning** and the input to **Design Review** (performed by a human).

The implementation must be usable as a bounded job. Containerization is an agent-specific deployment decision, not a system-wide mandate (`agentic-sdlc/docs/ARCHITECTURE.md`, "Deployment boundary"). Durable state belongs only in the supplied workspace, the target Git branch, and Conductor-owned workflow records.

## Required behavior

1. Accept a structured work request defined in [Integration](INTEGRATION.md).
2. Validate the request, repository identity, frozen intent commit, and the raw-byte `frozenArtifactSha256` before producing an artifact. Carry `contentSha256` through as provenance.
3. Work only in the assigned isolated workspace and `work/<intent-id>` branch.
4. Inspect the target repository and relevant repository-local instructions before design. Do not modify product code.
5. Create or update `.agent/work/<intent-id>/spec.md` and `.agent/work/<intent-id>/spec-run.json`.
6. Commit only the agent-owned engineering artifacts after validation succeeds.
7. Return a schema-valid structured result. The Conductor alone owns state transitions and Trello updates.

## Delivery increments

### 1. Contract and preflight

Implement request/result schema validation; path, branch, and identifier validation; frozen-intent integrity verification; and fail-closed status mapping. Add fixture tests for valid, missing, malformed, mismatched, and unapproved inputs.

### 2. Workspace and repository inspection

Create or receive the isolated workspace only from the explicit request. Verify the base commit and work branch, copy and hash-check the frozen `intent.md` if the Conductor has not already done so, and read repository-local instructions. Capture repository facts needed for the spec without modifying source code.

### 3. Specification production

Generate `spec.md` using the required structure in [Artifacts](ARTIFACTS.md). Preserve intent meaning, identify applicable repository constraints, and classify uncertainty. A decision that materially affects behavior, architecture, security, compliance, data semantics, destructive action, external contracts, cost, or scope must return `needs_decision`, not a guess.

### 4. Evidence and result

Write `spec-run.json`, validate the artifact set, commit it, and emit `spec_ready`, `needs_decision`, `blocked`, or `failed`. The result includes commit identity, artifact paths, concerns, and decision requests, but no secrets or hidden reasoning.

### 5. Operational hardening

Add structured, sanitized logging; timeouts; bounded repository inspection; cancellation handling; idempotency by work-item/run ID; and health/readiness endpoints if the chosen runtime is service-based. Do not claim production readiness without verifying these controls.

## Non-negotiable rules

- The frozen intent is immutable. If `frozenArtifactSha256` differs from the raw bytes of the workspace copy, stop with `blocked` / `INTENT_MUTATED`.
- The specification may iterate during Design Review, but every revision must retain provenance to the same frozen intent.
- A spec is not a test plan alone. It must state observable outcomes and preserve the distinction between test evidence and actual outcome delivery.
- Do not use this worker to create an implementation plan or product code. Those are later, separate stages.

## Technology choices

Do not select a language, framework, model provider, queue, or deployment platform merely from this document. Keep the interface transport-neutral and inject runtime configuration through environment variables or the Conductor request. Record the selected technology in an ADR before implementation.
