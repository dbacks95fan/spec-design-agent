# Build Instructions

## Objective

Build a stateless Spec & Design Agent that consumes a frozen product intent and policy profile and produces one versioned, reviewable specification plus a proposed machine-readable work contract. It is the first engineering-stage worker after **Prioritized** and runs when the Conductor moves a card into **Spec & Design**.

The implementation must be usable as a bounded job. Containerization is an agent-specific deployment decision, not a system-wide mandate (`agentic-sdlc/docs/ARCHITECTURE.md`, "Deployment boundary"). Durable state belongs only in the supplied workspace, the target Git branch, and Conductor-owned workflow records.

## Required behavior

1. Accept a structured work request defined in [Integration](INTEGRATION.md).
2. Validate the request, repository identity, frozen intent and policy-profile commits, and both raw-byte `frozenArtifactSha256` values before producing an artifact. Carry `contentSha256` through as provenance.
3. Work only in the assigned isolated workspace and `work/<intent-id>` branch.
4. Inspect the target repository and relevant repository-local instructions before design. Do not modify product code.
5. Create or update `.agent/work/<intent-id>/spec.md`, `.agent/work/<intent-id>/work-contract.yaml`, and `.agent/work/<intent-id>/spec-run.json`.
6. Commit only the agent-owned engineering artifacts after validation succeeds.
7. Return a schema-valid structured result. The Conductor alone owns state transitions and Trello updates.

## Delivery increments

### 1. Contract and preflight

Implement request/result schema validation; path, branch, and identifier validation; frozen-intent integrity verification; and fail-closed status mapping. Add fixture tests for valid, missing, malformed, mismatched, and unapproved inputs.

### 2. Workspace and repository inspection

Create or receive the isolated workspace only from the explicit request. Verify the base commit and work branch, copy and hash-check the frozen `intent.md` if the Conductor has not already done so, and read repository-local instructions. Capture repository facts needed for the spec without modifying source code.

### 3. Specification production

Generate `spec.md` using the required structure in [Artifacts](ARTIFACTS.md). Its implementation and validation sections are the sole human-readable plan; do not create `plan.md`. Generate a proposed `work-contract.yaml` from the same frozen inputs. Preserve intent meaning, identify applicable repository constraints and policy controls, and classify uncertainty. A decision that materially affects behavior, architecture, security, compliance, data semantics, destructive action, external contracts, cost, or scope must return `needs_decision`, not a guess.

### 4. Evidence and result

Write `spec-run.json`, validate the artifact set, commit it, and emit `spec_ready`, `needs_decision`, `blocked`, or `failed`. The result includes commit identity, artifact paths, concerns, and decision requests, but no secrets or hidden reasoning.

### 5. Operational hardening

Add structured, sanitized logging; timeouts; bounded repository inspection; cancellation handling; idempotency by work-item/run ID; and health/readiness endpoints if the chosen runtime is service-based. Do not claim production readiness without verifying these controls.

## Non-negotiable rules

- The frozen intent and policy profile are immutable. If either `frozenArtifactSha256` differs from the raw bytes of its workspace copy, stop with `blocked` and identify the mismatched input.
- The specification may iterate during Design Review, but every revision must retain provenance to the same frozen intent.
- A spec is not a test plan alone. It must state observable outcomes and preserve the distinction between test evidence and actual outcome delivery.
- Do not write product code, approve the spec or work contract, or change Trello state. The proposed work contract is an execution record, not a separate human-authored plan.

## Technology choices

Do not select a language, framework, model provider, queue, or deployment platform merely from this document. Keep the interface transport-neutral and inject runtime configuration through environment variables or the Conductor request. Record the selected technology in an ADR before implementation.
