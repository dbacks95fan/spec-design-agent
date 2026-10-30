# Build Instructions

## Objective

Build a stateless Spec & Design Agent that consumes a frozen product intent and policy profile and produces one versioned, reviewable specification plus a proposed machine-readable work contract. It is the first engineering-stage worker after **Prioritized** and runs when the Conductor moves a card into **Spec & Design**.

The implementation must be usable as a bounded job. Containerization is an agent-specific deployment decision, not a system-wide mandate (`agentic-sdlc/docs/ARCHITECTURE.md`, "Deployment boundary"). Durable state belongs only in the supplied workspace, the target Git branch, and Conductor-owned workflow records.

## Required behavior

1. Accept a structured work request defined in [Integration](INTEGRATION.md).
2. Accept only a Spec & Design invocation mapped from canonical StageInvocation 1.1. Verify the embedded Prioritized `FreezeActivationEvent`, work identity, and raw-byte hashes for both frozen intent and policy profile; there is no Ready-for-Planning approval field.
3. Clone the assigned target repository at the requested base commit into the supplied empty workspace. Create `work/<intent-id>` when it does not exist remotely; otherwise fetch and continue the existing branch. The agent commits and pushes only its authorized artifacts.
4. Copy both verified snapshots byte-for-byte into `.agent/work/<intent-id>/`, then inspect repository instructions, product constitution, architecture, code, interfaces, tests, and operational constraints without modifying product files.
5. Produce `spec.md` and a proposed Work Contract v3. Construct the contract from frozen identity, intent acceptance criteria and scope, policy controls, and repository-declared deterministic validation commands; validate it against the canonical WorkContract schema.
6. Validate the artifact set, write `spec-run.json`, commit only frozen copies and assigned engineering artifacts after validation succeeds, and push the work branch. A failed push is a failed stage result.
7. Return a schema-valid result correlated to the invocation, with commit/path/hash references for both outputs. The Conductor alone owns workflow state and Trello updates.

## Delivery increments

### 1. Contract and preflight

Implement request/result schema validation; path, branch, and identifier validation; Prioritized freeze identity checks; exact-byte integrity verification for both frozen inputs; and fail-closed status mapping. Add fixture tests for valid, missing, malformed, mismatched, and unauthorized inputs.

### 2. Workspace and repository inspection

Create or fetch the isolated work branch from the assigned target repository and base commit. Copy and hash-check both frozen snapshots, and read repository-local instructions plus the product constitution and architecture. Capture repository facts needed for the spec without modifying product source code.

### 3. Specification production

Generate `spec.md` using the required structure in [Artifacts](ARTIFACTS.md). Its implementation and validation sections are the sole human-readable plan; do not create `plan.md`. Construct and validate `work-contract.yaml` as Work Contract v3. Preserve intent meaning, consult product baselines and policy controls, and classify uncertainty. A decision that materially affects behavior, architecture, security, compliance, data semantics, destructive action, external contracts, cost, or scope must return `needs_decision`, not a guess.

### 4. Evidence and result

Write `spec-run.json`, validate schemas and exact-byte hashes, commit the artifact set, and emit `spec_ready`, `needs_decision`, `blocked`, or `failed`. `spec_ready` means both outputs are ready for human acceptance, never that they are accepted. The result includes invocation identity, commit identity, artifact paths and hashes, concerns, and decision requests, but no secrets or hidden reasoning.

### 5. Operational hardening

Add structured, sanitized logging; timeouts; bounded repository inspection; cancellation handling; idempotency by work-item/run ID; and health/readiness endpoints if the chosen runtime is service-based. Do not claim production readiness without verifying these controls.

## Non-negotiable rules

- The frozen intent and policy profile are immutable. If either Prioritized freeze hash differs from its raw snapshot bytes, stop with `blocked`.
- The specification may iterate during human review while the card remains in Spec & Design, but every revision must retain provenance to the same frozen intent and policy profile.
- A spec is not a test plan alone. It must state observable outcomes and preserve the distinction between test evidence and actual outcome delivery.
- Do not write product code, approve the spec or work contract, or change Trello state. The proposed work contract is an execution record, not a separate human-authored plan.

## Technology choices

Do not select a language, framework, model provider, queue, or deployment platform merely from this document. Keep the interface transport-neutral and inject runtime configuration through environment variables or the Conductor request. Record the selected technology in an ADR before implementation.
