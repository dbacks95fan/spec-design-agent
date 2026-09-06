# Agent Instructions

Read `docs/BUILD_INSTRUCTIONS.md` and `docs/OPERATING_CONTRACT.md` before making changes. Preserve the agent’s narrow boundary: turn a verified, immutable intent into reviewable specification and design artifacts.

- Treat the supplied frozen intent revision and hash as authoritative. Stop on a mismatch.
- Do not implement product code, update Trello, approve design, release, or change the intent.
- Distinguish verified facts, design decisions, assumptions, and unresolved human decisions.
- Prefer deterministic validation, schemas, and explicit error statuses over prompt-only compliance.
- Never record secrets, credentials, hidden reasoning, or private model traces in artifacts or logs.

Any material deviation needs a documented rationale, tradeoff, and an update to the appropriate contract.
