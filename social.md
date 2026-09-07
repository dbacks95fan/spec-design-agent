# Project Journal

## 2026-09-06

Created the design-agent contract as a standalone component: it validates an immutable intent, produces reviewable specification artifacts, and stops at human Design Review. Runtime and integration technology choices remain intentionally undecided.

### Later that day — runtime implementation (Praxis)

Read the new `agentic-sdlc` architecture repo end to end, then built the first runtime
for this agent against the contract docs. Choices recorded in ADR 0001: TypeScript ESM
on Node 20+, a bounded CLI job (no service), and a provider-neutral `SpecGenerator`
seam with `claude`, `codex`, and `mock` implementations picked by `SPEC_AGENT_PROVIDER`.

The pipeline: request validation → workspace isolation + `work/<id>` branch check →
byte-for-byte frozen-intent verification → bounded read-only repo inspection →
generation → structural `spec.md` validation → `spec-run.json` / `spec-result.json` +
one commit on the work branch. Fail-closed throughout: precondition failures become
`blocked`, open intent decisions or model-surfaced material decisions become
`needs_decision`, a malformed spec becomes `failed`.

80 tests green (unit + integration + end-to-end through the real CLI with the mock
provider). Not yet exercised: a live `claude`/`codex` run against a real product repo —
that stays a deployment-verification step.

Feeling: good about the shape. The provider seam kept the core logic clean, and TDD
caught the request-parse ordering bug (a `PreconditionError` escaping before the
structured-result path) early. Nothing strange at the Circle K.

### Same day — ported to Python (Praxis)

Sobe made two architecture calls: **all agents in Python**, and **every agent
containerized**. I'd chosen TypeScript from fleet convention rather than asking —
fair catch. Rewrote the whole agent in Python 3.12 on `uv`, module-for-module: same
pipeline, same `SpecGenerator` protocol (`claude` / `codex` / `mock`), same exit
codes, `jsonschema` in place of `ajv`, `pytest` in place of `node --test`. Deleted
the TypeScript tree. Updated `agentic-sdlc` to record both mandates in
`ARCHITECTURE.md` and the non-negotiables list.

One real Windows bite: `Path.write_text` translates `\n`→`\r\n`, so fixture intents
no longer matched their pinned hash and the integrity check (correctly) rejected
them. Added a `write_exact` helper that writes bytes, mirroring how the Conductor
stages the frozen intent. 80 tests green again. uv + `uv python install` had to be
bootstrapped on this box — noted for when the other agents get the same treatment.

### Same day — synced to the ratified agentic-sdlc contract (Praxis)

Sobe reviewed the doc-review findings and ratified them in `agentic-sdlc` (`f6f1724`),
but the outcome was not what my earlier journal entry assumed: the container
requirement was **explicitly rejected** ("no blanket container mandate"), and a
Python language mandate was **never ratified** — my edits adding both were
superseded and dropped. So Python + the Dockerfile are back to being *this agent's*
ADR-recorded choices, and I scrubbed every doc line that claimed an architecture
mandate.

Real contract change from the ratification: the freeze tuple now carries **two**
hashes. Reworked the request/artifact contract and the runtime — `intent.sha256`
became `intent.frozenArtifactSha256` (raw bytes, verified here) plus
`intent.contentSha256` (normalized rendering, carried as provenance into
`spec-run.json` and `spec.md` frontmatter, not verified). Also aligned stage names
to `WORKFLOW.md` ("Design Review", not "Human Design Review"). ~15 files, schemas +
runtime + tests + docs. 80 tests still green.

Flagged upstream: `intent-creation-skill` wasn't touched, so its `output-format.md`
(now the ratified canonical schema) still has one hash and its `SKILL.md` still
uses the retired board vocabulary. Not mine to fix.
