# Artifact Contracts

## Workspace layout

```text
.agent/work/INT-MF-0042/
  intent.md
  spec.md
  spec-run.json
```

`intent.md` is a byte-for-byte frozen input. The agent must not edit it.

## `spec.md`

Use this structure. Sections may be marked not relevant only when an explicit rationale is present.

```markdown
---
work_item: INT-MF-0042
product_id: MF
intent_commit: <sha>
intent_sha256: <hash>
base_commit: <sha>
spec_version: 1
status: draft
---

# Requirements and Design Specification

## Intent fidelity
## Confirmed repository context
## User and system-observable outcomes
## Functional requirements and acceptance criteria
## Non-functional requirements
## Design and affected boundaries
## Data, security, privacy, and compliance considerations
## Error handling and operational behavior
## Validation strategy
## Dependencies, assumptions, and non-goals
## Risks and unresolved decisions
## Traceability to frozen intent
```

The specification must distinguish confirmed facts from design decisions and assumptions. It must name affected boundaries and outcomes without prescribing product implementation code.

## `spec-run.json`

```json
{
  "runId": "uuid",
  "workItem": "INT-MF-0042",
  "productId": "MF",
  "intentCommit": "full-git-sha",
  "intentHash": "sha256",
  "baseCommit": "full-git-sha",
  "branch": "work/INT-MF-0042",
  "modelProvider": "configured-provider",
  "model": "configured-model",
  "agentVersion": "version",
  "promptVersion": "version-or-commit",
  "policyVersions": [],
  "startedAt": "RFC-3339 timestamp",
  "completedAt": "RFC-3339 timestamp",
  "status": "spec_ready"
}
```

Never store secrets, credentials, private chain-of-thought, or raw sensitive content in this record.

## Structured result

```json
{
  "runId": "uuid",
  "workItem": "INT-MF-0042",
  "status": "spec_ready",
  "summary": "Short factual summary",
  "branch": "work/INT-MF-0042",
  "workspace": "assigned workspace reference",
  "intentCommit": "full-git-sha",
  "intentHash": "sha256",
  "specCommit": "full-git-sha",
  "specPath": ".agent/work/INT-MF-0042/spec.md",
  "blockingConcerns": [],
  "nonBlockingConcerns": [],
  "humanDecisions": []
}
```

`humanDecisions` contains only specific, material decisions. A `spec_ready` result has no unresolved blocking decision.
