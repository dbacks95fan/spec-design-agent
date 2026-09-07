# Decisions and Open Questions

## Decided

- This is a standalone, stateless agent repository.
- It produces specification/design artifacts only; implementation planning and coding are later roles.
- The frozen intent revision and the freeze-tuple hashes are mandatory execution inputs.
- The Conductor owns workflow/Trello state; Design Review (performed by a human) remains a gate.
- The current operating model uses a Claude-oriented Coding Agent and Codex-oriented Evaluator; this agent’s own model provider remains configurable.

### Cross-component contracts honored (`agentic-sdlc/docs/CONTRACT_DECISIONS.md`, ratified `f6f1724`)

- **Canonical intent schema:** the sole canonical `intent.md` format is the Intent Creation Skill's `references/output-format.md`. This agent references it and does not parse a local variant.
- **Two-hash freeze tuple:** the request carries `intent.frozenArtifactSha256` (raw bytes — verified here) and `intent.contentSha256` (normalized rendering — carried as provenance into `spec-run.json` and `spec.md` frontmatter, not verified). Field names track `agentic-sdlc/docs/ARTIFACTS.md`.
- **Workflow vocabulary:** stage names follow `agentic-sdlc/docs/WORKFLOW.md` (`Design Review`, `Implementation Planning`, `Ready for Build`, `Coding`, `Evaluation`, `Ready for Release`).
- **Deployment:** no blanket container mandate. Runtime selection is this agent's decision, subject to bounded execution, least privilege, observability, and verified operational health.

### Agent-specific decisions (see `docs/adr/0001-runtime-technology.md`)

- **Runtime:** Python 3.12, managed with `uv` (`pyproject.toml` + `uv.lock`), tests with `pytest`. This agent's choice, not architecturally mandated.
- **Packaging:** ships as a non-root container image (uv build stage, `python:3.12` runtime, entrypoint = CLI). This agent's chosen delivery form, not a compliance requirement.
- **Transport:** a bounded CLI job (`spec-design-agent spec --request <file>`), no service runtime, no HTTP/health endpoints.
- **Model provider:** provider-neutral `SpecGenerator` seam with `claude`, `codex`, and `mock` implementations selected by `SPEC_AGENT_PROVIDER`; `claude-agent-sdk` is an optional extra.
- **Schema library:** `jsonschema` (draft-07).
- **Intent staging:** the agent consumes an already-staged frozen `intent.md`; it does not clone the intent-backlog repository. Absent staging returns `blocked` / `INTENT_NOT_STAGED`.
- **Git:** required on `PATH` for workspace verification and the single agent-owned artifact commit; commits are made without `--no-verify`.
- **Exit codes:** `0` spec_ready, `10` needs_decision, `20` blocked, `30` failed, `2` usage, `1` internal.
- **Extra artifact:** `spec-result.json` is persisted alongside `spec-run.json` to support `runId` idempotency and audit.

## Open before production

- Git authentication, branch/worktree provisioning owner, and commit-signing policy.
- Conductor transport (process vs. queue), callback authentication, retry policy, and result persistence outside the workspace.
- Product-specific sensitivity classification, retention, and observability integration.
- Behavior for a retry with a *new* `runId` against an already-approved `spec.md`: the current build increments `spec_version` and rewrites `spec.md`; explicit versioned retention of superseded specs is not yet implemented.
- A live `claude` / `codex` end-to-end run against a real product repository.
- `intent-creation-skill/references/output-format.md` still defines a single `intent_hash`, and `SKILL.md` still uses retired stage names (`Ready for Build → Agent Working → Agent Review → … → Done`). It is now the ratified canonical schema but has not been updated to the two-hash model or the `WORKFLOW.md` vocabulary. Tracked upstream, not here.
