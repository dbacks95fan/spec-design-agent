# Spec & Design Agent

A stateless engineering worker for an intent-driven Agentic SDLC. It turns one frozen product intent into a reviewable `spec.md`, design evidence, and a structured result for the Conductor and human Design Review.

It is not a coding agent, workflow orchestrator, evaluator, or release agent. It must not change the frozen intent, bypass human Design Review, or move Trello cards.

## Build from these documents

1. [Build instructions](docs/BUILD_INSTRUCTIONS.md) — required behavior and delivery increments.
2. [Operating contract](docs/OPERATING_CONTRACT.md) — inputs, outputs, artifacts, statuses, and invariants.
3. [Integration contract](docs/INTEGRATION.md) — the Conductor boundary and lifecycle handoff.
4. [Artifact contracts](docs/ARTIFACTS.md) — required `spec.md`, run record, and result shapes.
5. [Security and safety](docs/SECURITY.md) and [test strategy](docs/TEST_STRATEGY.md) — nonfunctional requirements.

## Status

This repository defines the agent contract. No runtime implementation is claimed yet.
