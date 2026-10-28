# Artifact Contracts

## Workspace layout

```text
.agent/inputs/<invocation-id>/
  intent.md                 # source snapshot staged for the invocation; read-only
  policy-profile.md         # source snapshot staged for the invocation; read-only
.agent/work/<intent-id>/
  intent.md                 # byte-identical frozen copy
  policy-profile.md         # byte-identical frozen copy
  spec.md
  work-contract.yaml
  spec-run.json
  spec-result.json          # saved terminal result for idempotent replay
```

The invocation input directory is supplied read-only. The agent writes only the assigned `.agent/work/<intent-id>/` directory and force-adds only the exact authorized artifact paths when committing. Repository ignore rules must not prevent durable outputs from being committed.

## `spec.md`

`spec.md` is the human-readable requirements, design, implementation, and validation plan. It has this frontmatter:

```yaml
work_item: INT-MF-0042
product_id: MF
intent_commit: <source commit SHA>
frozen_artifact_sha256: <raw-byte intent hash>
policy_profile_id: MF-DEFAULT
policy_profile_version: "1"
policy_profile_sha256: <raw-byte profile hash>
base_commit: <product repository base SHA>
spec_version: 1
status: draft
```

The required H2 sections, in order, are: Intent fidelity; Confirmed repository context; User and system-observable outcomes; Functional requirements and acceptance criteria; Non-functional requirements; Design and affected boundaries; Data, security, privacy, and compliance considerations; Error handling and operational behavior; Validation strategy; Dependencies, assumptions, and non-goals; Risks and unresolved decisions; Traceability to frozen intent.

The specification must distinguish confirmed facts, design decisions, and assumptions. It must refer to relevant product constitution and architecture sources when they materially shape the design. Tests are evidence, not proof of outcome delivery.

## `work-contract.yaml`

This is the proposed machine-readable Work Contract v3. The canonical definition is [`WorkContract`](https://github.com/dbacks95fan/agentic-sdlc/blob/main/schemas/lifecycle-contracts.schema.json#L215); this project bundles [`work-contract.schema.json`](../schemas/work-contract.schema.json) as a local validation copy. The canonical SDLC schema remains authoritative and the local copy must be kept synchronized.

The contract binds the exact work item, frozen intent and policy-profile references, target repository/base commit, acceptance criteria, included/excluded scope, required deterministic validation, policy controls/evidence, and release/observation requirements. Identity and immutable references come from the freeze event and request; the agent does not let generated prose alter them. The product owner accepts the Work Contract together with `spec.md` before Execution. Do not create `plan.md`.

## `spec-run.json`

The run record is validated against [`spec-run.schema.json`](../schemas/spec-run.schema.json) and records invocation provenance, work identity, both frozen input hashes and profile identity/version, target commit/branch, model/provider and prompt versions, timestamps, status, output version, and available usage. It must not contain secrets, credentials, raw sensitive content, or private model reasoning.

## Structured result

The response is validated against [`spec-result.schema.json`](../schemas/spec-result.schema.json). It repeats the invocation ID, triggering event, stage, and full work identity so the Conductor can correlate it. `spec_ready` requires one commit SHA, path, and raw-byte SHA-256 for each of `spec.md` and `work-contract.yaml`, plus the spec version. Other statuses include a concise summary and blocking concerns or specific human decisions as appropriate. The Conductor remains responsible for mapping successful output references into its canonical StageResult and recording human acceptance.
