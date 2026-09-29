# Integration Contract

## Conductor boundary

The Conductor owns workflow state, assignment, retries, concurrency, and Trello updates. This agent receives a bounded request and returns a bounded result. It does not poll Trello, select work, change priority, or trigger later stages.

```text
Prioritized
  -> Conductor validates frozen intent and policy profile
  -> card enters Spec & Design and invokes this agent
  -> agent produces spec.md and proposed work-contract.yaml
  -> human accepts both while the card remains in Spec & Design
  -> move into Execution invokes the Coding Agent
```

Stage names follow the canonical vocabulary in `agentic-sdlc/docs/WORKFLOW.md`
(`Prioritized -> Spec & Design -> Execution`). The human review is a gate inside Spec & Design, not a separate board column.

## Idempotency and retries

`runId` identifies one execution attempt; `workItem` identifies the lifecycle. Repeating the same `runId` must safely return the existing terminal result or fail with an explicit conflict. A retry receives a new `runId`, retains the same frozen intent reference, and never overwrites an approved artifact without versioning it.

## Design Review

Design Review is performed by a human. The agent’s successful result means *ready
for review*, not approved. Review feedback may revise `spec.md` while preserving
the same frozen intent. If feedback changes outcome, scope, acceptance criteria,
constraints, or assumptions materially, the agent returns `needs_decision` and the
organization creates a new intent/work item.

## Downstream planning handoff

The agent creates a proposed `work-contract.yaml` alongside `spec.md`; it does not create a separate `plan.md`. The product owner accepts both artifacts before Execution. The Coding Agent validates those accepted references before making code changes.
