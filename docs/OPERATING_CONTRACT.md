# Operating Contract

## Role

The agent translates a verified frozen intent into an implementable requirements and design specification for human review. It may inspect the target repository and write only its assigned artifact directory. It has no authority to alter intent, code, Trello state, approvals, or releases.

## Inputs

The Conductor supplies, at minimum:

```json
{
  "runId": "uuid",
  "workItem": "INT-MF-0042",
  "productId": "MF",
  "intent": {
    "repository": "org/intent-backlog",
    "commit": "full-git-sha",
    "path": "products/mealflow/intents/INT-MF-0042/intent.md",
    "frozenArtifactSha256": "lowercase-hex",
    "contentSha256": "lowercase-hex"
  },
  "target": {
    "repository": "org/product-repository",
    "baseCommit": "full-git-sha",
    "branch": "work/INT-MF-0042",
    "workspace": "assigned-absolute-path"
  },
  "approval": {
    "readyForPlanning": true,
    "approvedBy": "principal-or-system-id",
    "approvedAt": "RFC-3339 timestamp"
  }
}
```

The implementation may add optional, versioned fields; it must reject incompatible request versions rather than infer missing material information.

`intent.frozenArtifactSha256` and `intent.contentSha256` are the two hashes of the
Ready-for-Planning freeze tuple (`agentic-sdlc/docs/ARTIFACTS.md`, "Integrity and
freeze tuple"). This agent, as the first engineering-stage worker, verifies the
staged bytes against `frozenArtifactSha256`; `contentSha256` (the Intent Creation
Skill's normalized-rendering hash) is carried through as provenance and not
verified here.

## Preconditions

- `workItem`, `productId`, repositories, commits, branch, and workspace are valid and mutually consistent.
- Ready-for-Planning approval exists.
- The intent exists at the requested commit and its raw bytes match `intent.frozenArtifactSha256`.
- The workspace is isolated to the requested work item and based on the supplied base commit.
- The agent can write only `.agent/work/<work-item>/` and agent-owned metadata.

## Process

1. Validate the request and record a sanitized run start.
2. Verify the frozen intent and workspace integrity. Stop immediately on mismatch.
3. Read project instructions and inspect relevant code, interfaces, tests, architecture, and operational constraints.
4. Produce a specification grounded in the frozen intent and confirmed repository facts.
5. Validate the artifact and run record against schemas and integrity rules.
6. Commit agent-owned artifacts and return the structured result to the Conductor.

## Decision handling

Use `needs_decision` for material ambiguity. State the exact question, decision impact, options if known, and the minimum authorized role needed to decide. Use normal engineering judgment for choices already bounded by the frozen intent and existing repository standards.

## Statuses

| Status | Meaning | Conductor action |
| --- | --- | --- |
| `spec_ready` | Valid specification committed and ready for Design Review | Route to Design Review |
| `needs_decision` | A material decision is missing | Hold work and request human decision |
| `blocked` | Input, integrity, access, or environment precondition failed | Surface blocker; do not advance |
| `failed` | An unexpected execution failure occurred | Preserve safe diagnostics and apply retry policy |

## Invariants

The agent must never proceed from a mutable or mismatched intent, claim review approval, or present a passing test suite as proof that the requested product outcome will occur. It records conclusions and evidence, not private model reasoning.
