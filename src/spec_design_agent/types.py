# ABOUTME: Shared types for the Spec & Design Agent: work request, run record, structured
# ABOUTME: result, parsed frozen intent, and the fail-closed precondition error.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

SpecStatus = Literal["spec_ready", "needs_decision", "blocked", "failed"]

# The request-contract version this build understands.
SUPPORTED_REQUEST_VERSION = 2


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
    content_sha256: str | None


@dataclass(frozen=True)
class TargetRef:
    repository: str
    base_commit: str
    branch: str
    workspace: str


@dataclass(frozen=True)
class PolicyProfileRef:
    repository: str
    commit: str
    path: str
    frozen_artifact_sha256: str
    profile_id: str
    version: str


@dataclass(frozen=True)
class FreezeActivation:
    event_id: str
    authorized_by: str
    recorded_at: str
    product_id: str
    intent_id: str
    intent_version: int
    trello_card_id: str


@dataclass(frozen=True)
class SpecRequest:
    run_id: str
    invocation_id: str
    trigger_event_id: str
    stage: str
    work_item: str
    product_id: str
    intent: IntentRef
    policy_profile: PolicyProfileRef
    freeze_activation: FreezeActivation
    target: TargetRef
    read_paths: list[str]
    write_paths: list[str]
    request_version: int = 2

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> "SpecRequest":
        freeze = raw["freezeActivation"]
        frozen_work = freeze["work_item"]
        intent_ref = freeze["intent"]
        profile_ref = freeze["policy_profile"]
        return SpecRequest(
            run_id=raw["runId"],
            invocation_id=raw["invocationId"],
            trigger_event_id=raw["triggerEventId"],
            stage=raw["stage"],
            work_item=raw["workItem"],
            product_id=raw["productId"],
            intent=IntentRef(
                repository=intent_ref["repository"],
                commit=intent_ref["commit_sha"],
                path=intent_ref["path"],
                frozen_artifact_sha256=intent_ref["sha256"],
                content_sha256=raw.get("intentContentSha256"),
            ),
            policy_profile=PolicyProfileRef(
                repository=profile_ref["repository"],
                commit=profile_ref["commit_sha"],
                path=profile_ref["path"],
                frozen_artifact_sha256=profile_ref["sha256"],
                profile_id=freeze["policy_profile_id"],
                version=freeze["policy_profile_version"],
            ),
            freeze_activation=FreezeActivation(
                event_id=freeze["event_id"],
                authorized_by=freeze["authorized_by"],
                recorded_at=freeze["recorded_at"],
                product_id=frozen_work["product_id"],
                intent_id=frozen_work["intent_id"],
                intent_version=frozen_work["intent_version"],
                trello_card_id=frozen_work["trello_card_id"],
            ),
            target=TargetRef(
                repository=raw["target"]["repository"],
                base_commit=raw["target"]["baseCommit"],
                branch=raw["target"]["branch"],
                workspace=raw["target"]["workspace"],
            ),
            read_paths=list(raw["readPaths"]),
            write_paths=list(raw["writePaths"]),
            request_version=int(raw["requestVersion"]),
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
    invocation_id: str
    trigger_event_id: str
    stage: str
    work_item: str
    product_id: str
    intent_version: int
    trello_card_id: str
    status: SpecStatus
    summary: str
    branch: str
    workspace: str
    intent_commit: str
    frozen_artifact_sha256: str
    policy_profile_id: str
    policy_profile_version: str
    policy_profile_sha256: str
    intent_content_sha256: str | None
    blocking_concerns: list[str] = field(default_factory=list)
    non_blocking_concerns: list[str] = field(default_factory=list)
    human_decisions: list[HumanDecision] = field(default_factory=list)
    spec_commit: str | None = None
    spec_path: str | None = None
    spec_sha256: str | None = None
    spec_version: int | None = None
    work_contract_path: str | None = None
    work_contract_sha256: str | None = None
    # Token/cost totals for the generation, when the provider reports them.
    usage: dict[str, Any] | None = None

    def to_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "runId": self.run_id,
            "invocationId": self.invocation_id,
            "triggerEventId": self.trigger_event_id,
            "stage": self.stage,
            "workItem": self.work_item,
            "productId": self.product_id,
            "intentVersion": self.intent_version,
            "trelloCardId": self.trello_card_id,
            "status": self.status,
            "summary": self.summary,
            "branch": self.branch,
            "workspace": self.workspace,
            "intentCommit": self.intent_commit,
            "frozenArtifactSha256": self.frozen_artifact_sha256,
            "policyProfileId": self.policy_profile_id,
            "policyProfileVersion": self.policy_profile_version,
            "policyProfileSha256": self.policy_profile_sha256,
            "blockingConcerns": list(self.blocking_concerns),
            "nonBlockingConcerns": list(self.non_blocking_concerns),
            "humanDecisions": [d.to_json() for d in self.human_decisions],
        }
        if self.intent_content_sha256 is not None:
            out["intentContentSha256"] = self.intent_content_sha256
        if self.spec_commit is not None:
            out["specCommit"] = self.spec_commit
        if self.spec_path is not None:
            out["specPath"] = self.spec_path
        if self.spec_sha256 is not None:
            out["specSha256"] = self.spec_sha256
        if self.spec_version is not None:
            out["specVersion"] = self.spec_version
        if self.work_contract_path is not None:
            out["workContractPath"] = self.work_contract_path
        if self.work_contract_sha256 is not None:
            out["workContractSha256"] = self.work_contract_sha256
        if self.usage is not None:
            out["usage"] = self.usage
        return out


@dataclass
class SpecRunRecord:
    run_id: str
    invocation_id: str
    trigger_event_id: str
    work_item: str
    product_id: str
    intent_commit: str
    frozen_artifact_sha256: str
    policy_profile_id: str
    policy_profile_version: str
    policy_profile_sha256: str
    intent_content_sha256: str | None
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
            "invocationId": self.invocation_id,
            "triggerEventId": self.trigger_event_id,
            "workItem": self.work_item,
            "productId": self.product_id,
            "intentCommit": self.intent_commit,
            "frozenArtifactSha256": self.frozen_artifact_sha256,
            "policyProfileId": self.policy_profile_id,
            "policyProfileVersion": self.policy_profile_version,
            "policyProfileSha256": self.policy_profile_sha256,
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
        if self.intent_content_sha256 is not None:
            out["intentContentSha256"] = self.intent_content_sha256
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
    trello_card_id: str | None = None
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
