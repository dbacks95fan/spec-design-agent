# Integration Contract

## Conductor boundary

The Conductor owns workflow state, assignment, retries, concurrency, and Trello updates. This agent receives a bounded request and returns a bounded result. It does not poll Trello, select work, change priority, or trigger later stages.

```text
Ready for Planning
  -> Conductor validates approval and freezes intent revision
  -> Spec & Design Agent validates and produces specification
  -> Conductor posts a decision brief and routes to Human Design Review
  -> Human approval enables the separate Implementation Planning stage
```

## Idempotency and retries

`runId` identifies one execution attempt; `workItem` identifies the lifecycle. Repeating the same `runId` must safely return the existing terminal result or fail with an explicit conflict. A retry receives a new `runId`, retains the same frozen intent reference, and never overwrites an approved artifact without versioning it.

## Human Design Review

The agent’s successful result means *ready for review*, not approved. Review feedback may revise `spec.md` while preserving the same frozen intent. If feedback changes outcome, scope, acceptance criteria, constraints, or assumptions materially, the agent returns `needs_decision` and the organization creates a new intent/work item.

## Downstream planning handoff

Only an approved `spec.md` becomes input to the separate Implementation Planning stage. The planning worker is responsible for `plan.md` and the work contract; this agent must not create either as a substitute for design review.
