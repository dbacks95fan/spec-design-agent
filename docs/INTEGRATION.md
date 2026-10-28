# Integration Contract

## Conductor boundary

The Conductor owns lifecycle state, assignment, retries, concurrency, and Trello updates. It invokes this worker only after validating a card's transition into Spec & Design and its active Prioritized freeze. It does not delegate policy decisions or human acceptance to the agent.

The Conductor maps canonical StageInvocation 1.1 into `schemas/spec-request.schema.json` version 2. The request preserves `invocation_id`, `trigger_event_id`, stage, full work identity, target commit, workspace reference, read/write permissions, and the complete typed `FreezeActivationEvent`. The frozen intent and policy profile are identified by the event's distinct `intent` and `policy_profile` ArtifactRefs; they are not inferred from list order or file names.

The invocation runtime makes byte-preserving snapshots available at `.agent/inputs/<invocationId>/intent.md` and `.agent/inputs/<invocationId>/policy-profile.md`. The agent checks these snapshots against their ArtifactRef hashes, copies them into `.agent/work/<intent-id>/`, and reports the same invocation ID and work identity in its result. A mismatch blocks the stage. The Conductor rechecks that the freeze remains active before accepting the result.

```text
Prioritized
  -> Conductor validates and records the freeze
  -> card enters Spec & Design and invokes this agent
  -> agent verifies both frozen inputs and produces spec.md + work-contract.yaml
  -> product owner accepts or returns both artifacts in Spec & Design
  -> accepted references are frozen; card enters Execution
```

The human review is a gate inside Spec & Design, not another board column. `spec_ready` means ready for that decision and cannot advance the card.

## Result mapping

`spec-result.schema.json` defines the agent response. It includes invocation correlation, work identity, stage-specific status, concerns and decision requests. On `spec_ready`, it includes the target commit, repository-relative path, and raw-byte SHA-256 for both output artifacts. The Conductor validates the response and maps those references to the canonical StageResult output artifact references; it records the separate Spec Acceptance Record only after the human accepts both artifacts.

## Idempotency and rework

`runId` identifies one attempt; `invocationId` identifies the Conductor stage invocation; `workItem` identifies the lifecycle. Repeating the same `runId` returns the saved terminal result without regenerating output. A retry uses a new invocation/run ID and the same active freeze unless the Conductor has recorded a successor lifecycle. The agent cannot overwrite an accepted output; human review revisions receive a new spec version and commit while retaining the same frozen inputs.

If review uncovers a material change to outcome, scope, acceptance criteria, policy applicability, architecture, or external contract, the agent returns `needs_decision`; the accountable human decides whether to create a new intent lifecycle. The agent does not infer rerun or out-of-order board behavior.
