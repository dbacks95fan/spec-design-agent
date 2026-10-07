# ABOUTME: Shared types for the Spec & Design Agent: work request, run record, structured
# ABOUTME: result, parsed frozen intent, and the fail-closed precondition error.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

SpecStatus = Literal["spec_ready", "needs_decision", "blocked", "failed"]

# The request-contract version this build understands.
SUPPORTED_REQUEST_VERSION = 1


@dataclass(frozen=True)
class IntentRef:
    repository: str
    commit: str
    path: str
    # SHA-256 of the raw bytes of the exact frozen intent.md snapshot. This agent
    # verifies the staged copy against it (agentic-sdlc/docs/ARTIFACTS.md).
    frozen_artifact_sha256: str
    # SHA-256 of the Intent Creation Skill's canonical normalized rendering.
    # Retained as provenance only; not verified here.
    content_sha256: str


@dataclass(frozen=True)
class TargetRef:
    repository: str
    base_commit: str
    branch: str
    workspace: str


@dataclass(frozen=True)
class Approval:
    ready_for_planning: bool
    approved_by: str
    approved_at: str


@dataclass(frozen=True)
class SpecRequest:
    run_id: str
    work_item: str
    product_id: str
    intent: IntentRef
    target: TargetRef
    approval: Approval
    request_version: int = 1

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> "SpecRequest":
        return SpecRequest(
            run_id=raw["runId"],
            work_item=raw["workItem"],
            product_id=raw["productId"],
            intent=IntentRef(
                repository=raw["intent"]["repository"],
                commit=raw["intent"]["commit"],
                path=raw["intent"]["path"],
                frozen_artifact_sha256=raw["intent"]["frozenArtifactSha256"],
                content_sha256=raw["intent"]["contentSha256"],
            ),
            target=TargetRef(
                repository=raw["target"]["repository"],
                base_commit=raw["target"]["baseCommit"],
                branch=raw["target"]["branch"],
                workspace=raw["target"]["workspace"],
            ),
            approval=Approval(
                ready_for_planning=bool(raw["approval"]["readyForPlanning"]),
                approved_by=raw["approval"]["approvedBy"],
                approved_at=raw["approval"]["approvedAt"],
            ),
            request_version=int(raw.get("requestVersion", 1)),
        )


@dataclass
class HumanDecision:
    question: str
    impact: str
    minimum_authority: str
    options: list[str] | None = None

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "question": self.question,
            "impact": self.impact,
            "minimumAuthority": self.minimum_authority,
        }
        if self.options:
            out["options"] = list(self.options)
        return out


@dataclass
class SpecResult:
    run_id: str
    work_item: str
    status: SpecStatus
    summary: str
    branch: str
    workspace: str
    intent_commit: str
    frozen_artifact_sha256: str
    intent_content_sha256: str
    blocking_concerns: list[str] = field(default_factory=list)
    non_blocking_concerns: list[str] = field(default_factory=list)
    human_decisions: list[HumanDecision] = field(default_factory=list)
    spec_commit: str | None = None
    spec_path: str | None = None
    spec_version: int | None = None
    # Token/cost totals for the generation, when the provider reports them.
    usage: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "runId": self.run_id,
            "workItem": self.work_item,
            "status": self.status,
            "summary": self.summary,
            "branch": self.branch,
            "workspace": self.workspace,
            "intentCommit": self.intent_commit,
            "frozenArtifactSha256": self.frozen_artifact_sha256,
            "intentContentSha256": self.intent_content_sha256,
            "blockingConcerns": list(self.blocking_concerns),
            "nonBlockingConcerns": list(self.non_blocking_concerns),
            "humanDecisions": [d.to_json() for d in self.human_decisions],
        }
        if self.spec_commit is not None:
            out["specCommit"] = self.spec_commit
        if self.spec_path is not None:
            out["specPath"] = self.spec_path
        if self.spec_version is not None:
            out["specVersion"] = self.spec_version
        if self.usage is not None:
            out["usage"] = self.usage
        return out


@dataclass
class SpecRunRecord:
    run_id: str
    work_item: str
    product_id: str
    intent_commit: str
    frozen_artifact_sha256: str
    intent_content_sha256: str
    base_commit: str
    branch: str
    model_provider: str
    model: str
    agent_version: str
    prompt_version: str
    started_at: str
    completed_at: str
    status: SpecStatus
    policy_versions: list[str] = field(default_factory=list)
    spec_version: int | None = None
    # Token/cost totals for the generation, when the provider reports them.
    usage: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "runId": self.run_id,
            "workItem": self.work_item,
            "productId": self.product_id,
            "intentCommit": self.intent_commit,
            "frozenArtifactSha256": self.frozen_artifact_sha256,
            "intentContentSha256": self.intent_content_sha256,
            "baseCommit": self.base_commit,
            "branch": self.branch,
            "modelProvider": self.model_provider,
            "model": self.model,
            "agentVersion": self.agent_version,
            "promptVersion": self.prompt_version,
            "policyVersions": list(self.policy_versions),
            "startedAt": self.started_at,
            "completedAt": self.completed_at,
            "status": self.status,
        }
        if self.spec_version is not None:
            out["specVersion"] = self.spec_version
        if self.usage is not None:
            out["usage"] = self.usage
        return out


@dataclass
class ParsedIntent:
    intent_id: str
    status: str
    sha256: str
    raw: str
    product_id: str | None = None
    version: int | None = None
    open_decisions: list[str] = field(default_factory=list)
    acceptance_criteria: list[str] = field(default_factory=list)
    sections: dict[str, str] = field(default_factory=dict)


class PreconditionError(Exception):
    """A defect class that maps to a non-success terminal status without leaking internals."""

    def __init__(self, status: Literal["blocked", "needs_decision"], code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


class RequestValidationError(Exception):
    """Structural problems with the request object (a usage error)."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("Work request failed validation: " + "; ".join(errors))
        self.errors = errors
