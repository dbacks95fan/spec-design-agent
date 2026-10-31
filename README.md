# Spec & Design Agent

A stateless engineering worker invoked when a card enters **Spec & Design** after the Conductor records the Prioritized freeze. It verifies the frozen intent and policy profile, then produces `spec.md` and a proposed Work Contract v3 for human acceptance while the card remains in Spec & Design.

It is not a coding agent, workflow orchestrator, evaluator, or release agent. It must not change frozen inputs, write product code, approve its own outputs, or move Trello cards.

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

For the assigned product-code repository, the process that launches the agent must provide a short-lived GitHub App installation token with read/write access as `SPEC_AGENT_GITHUB_TOKEN`. The App private key stays with the token-minting provider and is never passed to the agent. Do not use `GITHUB_TOKEN`, a personal access token, or a developer's ambient GitHub login as a fallback. The agent does not access `intent-backlog`; it uses the frozen snapshot supplied with its request and the assigned repository, independent of the source Trello board.

### Model provider

The spec generator is provider-neutral, selected by `SPEC_AGENT_PROVIDER`:

| Provider | How it runs | Notes |
| --- | --- | --- |
| `claude` (default) | Claude Agent SDK with read-only tools over the workspace | needs the optional `claude` extra and `ANTHROPIC_API_KEY` |
| `codex` | `codex exec --sandbox read-only` from the workspace | needs the Codex CLI on `PATH` and an authenticated local Codex CLI session |
| `mock` | deterministic, offline | used by the test suite and for dry runs |

`SPEC_AGENT_MODEL` overrides the model id. See `.env.example` for the full set of
knobs (timeout, inspection bounds).

### Exit codes

```text
0   spec_ready       spec.md and Work Contract v3 committed, ready for human acceptance
10  needs_decision   a material decision is missing (see result.humanDecisions)
20  blocked          an input / integrity / access / environment precondition failed
30  failed           an unexpected execution failure occurred
2   usage error
1   internal error
```

### What a run does

1. Validate request version, Spec & Design stage, work identity, and the embedded Prioritized freeze event. No separate Ready-for-Planning approval is accepted.
2. Clone the target repository at the requested base commit, then create `work/<intent-id>` or fetch that existing remote branch.
3. Verify the raw bytes of both frozen input snapshots against their `ArtifactRef` hashes, then copy them into `.agent/work/<work-item>/`.
4. Read repository instructions, the product constitution and architecture, and bounded repository facts without changing product files.
5. Generate `spec.md`; build Work Contract v3 from the verified intent, policy profile, and repository-declared validation commands. A material unresolved decision returns `needs_decision`.
6. Validate both outputs against their contracts, record provenance, commit the frozen copies, `spec.md`, `work-contract.yaml`, and `spec-run.json`, then push the work branch. The result returns invocation identity plus commit, path, and hash references for both outputs.

Repeating a request with the same `runId` returns the existing terminal result without re-running. `schemas/work-contract.schema.json` is a local validation copy; `agentic-sdlc/schemas/lifecycle-contracts.schema.json` remains authoritative.

## Container

Containerization is this agent's chosen delivery form, not an architecture mandate
(`agentic-sdlc/docs/CONTRACT_DECISIONS.md`, "Deployment"). The provided image is
one supported way to run the bounded job.

```bash
docker compose run --rm spec-design-agent spec --request /work/INT-MF-0042/request.json
```

The image entrypoint is the CLI, runs as a non-root user, and needs `git`. The
Orchestrator mounts the invocation bundle at `/work`; the agent clones the
product repository into `/work/repository` and creates or fetches the work branch.

## Status

The agent contract and a Python runtime implementation are in place, with unit,
integration, and end-to-end tests using the deterministic `mock` provider. The
agent creates or fetches and pushes its own work branch. A live `claude` / `codex`
run against a real product repository has not been exercised here and remains a
deployment-verification step.
