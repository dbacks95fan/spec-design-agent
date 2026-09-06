# Decisions and Open Questions

## Decided

- This is a standalone, stateless agent repository.
- It produces specification/design artifacts only; implementation planning and coding are later roles.
- The frozen intent revision and SHA-256 hash are mandatory execution inputs.
- The Conductor owns workflow/Trello state; human Design Review remains a gate.
- The current operating model uses a Claude-oriented Coding Agent and Codex-oriented Evaluator; this agent’s own model provider remains configurable.

## Open before implementation

- Runtime language, framework, container interface, and model provider.
- Exact JSON Schema versions and artifact-validation library.
- Git authentication, branch/worktree provisioning owner, and commit-signing policy.
- Conductor transport, callback authentication, retry policy, and status persistence.
- Product-specific sensitivity classification, retention, and observability integration.
