# Spec & Design Agent

A stateless engineering worker for an intent-driven Agentic SDLC. It turns one frozen product intent into a reviewable `spec.md`, a run record, and a structured result for the Conductor and Design Review (performed by a human).

It is not a coding agent, workflow orchestrator, evaluator, or release agent. It must not change the frozen intent, bypass Design Review, or move Trello cards.

## Contract documents

1. [Build instructions](docs/BUILD_INSTRUCTIONS.md) — required behavior and delivery increments.
2. [Operating contract](docs/OPERATING_CONTRACT.md) — inputs, outputs, artifacts, statuses, and invariants.
3. [Integration contract](docs/INTEGRATION.md) — the Conductor boundary and lifecycle handoff.
4. [Artifact contracts](docs/ARTIFACTS.md) — required `spec.md`, run record, and result shapes.
5. [Security and safety](docs/SECURITY.md) and [test strategy](docs/TEST_STRATEGY.md) — nonfunctional requirements.
6. [ADR 0001](docs/adr/0001-runtime-technology.md) — runtime technology decisions.

## Runtime

Python 3.12, managed with [uv](https://docs.astral.sh/uv/). The agent is a bounded
CLI job: it reads one Conductor request and prints one JSON result to stdout. Logs
are structured JSON on stderr.

```bash
uv sync                       # install (add --extra claude for the Claude provider)
uv run pytest                 # unit + integration + end-to-end, pristine output required

uv run spec-design-agent spec --request /path/to/request.json --provider claude
# or: python -m spec_design_agent spec --request /path/to/request.json
```

`request.json` follows `schemas/spec-request.schema.json` (see `docs/OPERATING_CONTRACT.md`).
The result follows `schemas/spec-result.schema.json`.

### Model provider

The spec generator is provider-neutral, selected by `SPEC_AGENT_PROVIDER`:

| Provider | How it runs | Notes |
| --- | --- | --- |
| `claude` (default) | Claude Agent SDK with read-only tools over the workspace | needs the optional `claude` extra and `ANTHROPIC_API_KEY` |
| `codex` | `codex exec --sandbox read-only` from the workspace | needs the Codex CLI on `PATH` and `OPENAI_API_KEY` |
| `mock` | deterministic, offline | used by the test suite and for dry runs |

`SPEC_AGENT_MODEL` overrides the model id. See `.env.example` for the full set of
knobs (timeout, inspection bounds).

### Exit codes

```text
0   spec_ready       spec.md committed to the work branch, ready for Design Review
10  needs_decision   a material decision is missing (see result.humanDecisions)
20  blocked          an input / integrity / access / environment precondition failed
30  failed           an unexpected execution failure occurred
2   usage error
1   internal error
```

### What a run does

1. Validate the request shape, then the Ready-for-Planning approval and identity consistency.
2. Verify the workspace is an isolated Git work tree on `work/<work-item>` based on the requested base commit.
3. Verify the staged frozen `intent.md` byte-for-byte against `request.intent.frozenArtifactSha256`; carry `request.intent.contentSha256` through as provenance.
4. Inspect the target repository read-only, within `SPEC_AGENT_*` bounds.
5. Generate `spec.md` via the configured provider; a material decision returns `needs_decision` with no commit.
6. Validate `spec.md` structurally (all required sections, no unresolved markers), write `spec-run.json` and `spec-result.json`, and commit `.agent/work/<work-item>/` on the work branch.

Repeating a request with the same `runId` returns the existing terminal result without re-running.

## Container

Containerization is this agent's chosen delivery form, not an architecture mandate
(`agentic-sdlc/docs/CONTRACT_DECISIONS.md`, "Deployment"). The provided image is
one supported way to run the bounded job.

```bash
docker compose run --rm spec-design-agent spec --request /work/INT-MF-0042/request.json
```

The image entrypoint is the CLI, runs as a non-root user, and needs `git`. The
Conductor mounts the isolated work-item workspace at `/work`.

## Status

The agent contract and a Python runtime implementation are in place, with unit,
integration, and end-to-end tests using the deterministic `mock` provider. A live
`claude` / `codex` end-to-end run against a real repository has not been exercised
here and remains a deployment-verification step.
