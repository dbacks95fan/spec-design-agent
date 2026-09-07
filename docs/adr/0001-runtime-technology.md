# ADR 0001 — Runtime technology for the Spec & Design Agent

- Status: Accepted
- Date: 2026-09-06
- Revised: 2026-09-06, after `agentic-sdlc` contract ratification (`f6f1724`)
- Context docs: `docs/BUILD_INSTRUCTIONS.md`, `docs/OPERATING_CONTRACT.md`, `docs/INTEGRATION.md`, `agentic-sdlc/docs/CONTRACT_DECISIONS.md`
- Supersedes: an earlier TypeScript implementation of this agent (never released)

## Context

`docs/BUILD_INSTRUCTIONS.md` requires that language, framework, model provider, and
deployment platform be recorded in an ADR before implementation, and that the
interface stay transport-neutral. The agent is a stateless, bounded worker that
consumes one Conductor request and returns one structured result.

The `agentic-sdlc` architecture does **not** mandate an implementation language,
and it explicitly does **not** impose a blanket container requirement
(`agentic-sdlc/docs/CONTRACT_DECISIONS.md`, "Deployment";
`agentic-sdlc/docs/ARCHITECTURE.md`, "Deployment boundary"). The choices below are
therefore this agent's own, made for fleet consistency and operability, not to
satisfy an architectural rule. What the architecture *does* require of every
runtime: bounded execution, least privilege, observability, and verified
operational health.

## Decision

1. **Language / runtime:** Python 3.12, managed with **uv** (`pyproject.toml` +
   `uv.lock`). Chosen for this agent; not architecturally mandated.
2. **Transport:** a bounded CLI job — `spec-design-agent spec --request <file>`
   (also `python -m spec_design_agent ...`) — that reads one request and writes
   one JSON result to stdout. No long-lived service; there is no service-based
   runtime, so no HTTP or health endpoints are built. `docs/INTEGRATION.md`'s
   Conductor boundary is satisfied by process invocation and exit codes.
3. **Model provider:** provider-neutral. A `SpecGenerator` protocol has three
   implementations — `claude` (Claude Agent SDK, read-only tools), `codex`
   (`codex exec --sandbox read-only`), and `mock` (deterministic, for tests and
   offline runs). Selection is by `SPEC_AGENT_PROVIDER`; nothing is hardcoded.
   `claude-agent-sdk` is an optional extra (`uv sync --extra claude`).
4. **Schema validation:** JSON Schema (draft-07) validated with `jsonschema`.
5. **Frozen-intent format:** the sole canonical `intent.md` schema, owned by the
   Intent Creation Skill (`references/output-format.md`) — YAML frontmatter plus H2
   sections. This agent does not define or parse a local variant
   (`agentic-sdlc/docs/CONTRACT_DECISIONS.md`, "Canonical intent representation").
6. **Freeze-tuple hashes:** the request carries both hashes of the freeze tuple.
   As the first engineering-stage worker, this agent verifies the staged raw bytes
   against `frozenArtifactSha256` (mismatch -> `blocked` / `INTENT_MUTATED`) and
   carries `contentSha256` (the normalized-rendering hash) through to
   `spec-run.json` and `spec.md` frontmatter as provenance, without verifying it
   (`agentic-sdlc/docs/ARTIFACTS.md`, "Integrity and freeze tuple").
7. **Intent staging:** the agent uses a frozen `intent.md` already present in the
   workspace (either under `.agent/work/<work-item>/` or at the request's
   `intent.path`). It does not clone the intent-backlog repository itself; if no
   frozen intent is staged, it returns `blocked` / `INTENT_NOT_STAGED`.
8. **Packaging:** a two-stage, non-root `Dockerfile` (uv build stage, `python:3.12`
   runtime) whose entrypoint is the CLI, plus a one-shot `compose.yaml`. This is
   this agent's chosen delivery form, not a compliance requirement; the operator
   picks the platform and registry.
9. **Exit codes:** `0` spec_ready, `10` needs_decision, `20` blocked, `30` failed,
   `2` usage error, `1` internal error.

## Consequences

- A new provider is a new `SpecGenerator` implementation plus one branch in the
  `create_generator` factory; no other module changes.
- The agent depends on `git` being available for workspace verification and the
  single agent-owned artifact commit.
- Because there is no service runtime, operational concerns (retries, concurrency,
  scheduling) remain with the Conductor, as the architecture intends.
- Structural spec validation is deterministic; semantic intent-fidelity review
  stays a human Design Review gate (the `Design Review` stage in
  `agentic-sdlc/docs/WORKFLOW.md`).
- Tests must write the frozen intent as exact bytes (no OS newline translation),
  mirroring how the Conductor stages it, or the integrity check rejects the copy.
