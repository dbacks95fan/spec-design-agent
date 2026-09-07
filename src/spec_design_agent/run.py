# ABOUTME: Orchestrates one Spec & Design run: preflight -> workspace -> integrity -> inspect
# ABOUTME: -> generate -> validate -> commit. Maps every failure to a fail-closed terminal status.

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import git
from .config import AgentConfig, load_config
from .generators import create_generator
from .generators.base import SpecGenerationInput, SpecGenerator
from .integrity import verify_frozen_intent
from .intent import read_intent_file
from .logging_ import error_message, log
from .prompt import PROMPT_VERSION
from .repo_inspect import inspect_repository
from .request import check_request_preconditions, validate_request_shape
from .result import build_result
from .spec import SpecFrontmatter, assemble_spec, validate_spec
from .spec_run import build_run_record
from .types import HumanDecision, PreconditionError, SpecRequest, SpecResult, SpecRunRecord, SpecStatus
from .workspace import prepare_workspace

EXIT_CODES: dict[SpecStatus, int] = {
    "spec_ready": 0,
    "needs_decision": 10,
    "blocked": 20,
    "failed": 30,
}

_ZERO_HASH = "0" * 64


@dataclass
class RunOutcome:
    result: SpecResult
    run_record: SpecRunRecord | None
    exit_code: int


def _now_iso(now: Callable[[], datetime]) -> str:
    return now().astimezone(timezone.utc).isoformat()


def _read_json_if_present(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _with_timeout(work: Callable[[threading.Event], Any], timeout_ms: int) -> Any:
    cancel = threading.Event()
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(work, cancel)
        try:
            return future.result(timeout=timeout_ms / 1000)
        except FuturesTimeout as exc:
            cancel.set()
            raise TimeoutError(f"generation exceeded {timeout_ms}ms") from exc


def run_spec_design(
    raw_request: Any,
    *,
    config: AgentConfig | None = None,
    generator: SpecGenerator | None = None,
    now: Callable[[], datetime] | None = None,
) -> RunOutcome:
    cfg = config or load_config()
    now = now or (lambda: datetime.now(timezone.utc))
    started_at = _now_iso(now)

    # Structural validation is a usage error (raised to the caller). Everything after
    # this point can be expressed as a structured terminal result for the Conductor.
    request: SpecRequest = validate_request_shape(raw_request)
    log("info", "run.started", "Spec & Design run started.", runId=request.run_id, workItem=request.work_item)

    def finish(
        status: SpecStatus,
        summary: str,
        *,
        blocking_concerns: list[str] | None = None,
        non_blocking_concerns: list[str] | None = None,
        human_decisions: list[HumanDecision] | None = None,
        frozen_artifact_sha256: str = _ZERO_HASH,
        provenance: dict[str, Any] | None = None,
    ) -> RunOutcome:
        result = build_result(
            request=request,
            status=status,
            summary=summary,
            frozen_artifact_sha256=frozen_artifact_sha256,
            blocking_concerns=blocking_concerns,
            non_blocking_concerns=non_blocking_concerns,
            human_decisions=human_decisions,
            spec_commit=(provenance or {}).get("spec_commit"),
            spec_path=(provenance or {}).get("spec_path"),
            spec_version=(provenance or {}).get("spec_version"),
        )
        run_record: SpecRunRecord | None = None
        if provenance:
            run_record = build_run_record(
                request=request,
                base_commit=provenance["base_commit"],
                frozen_artifact_sha256=frozen_artifact_sha256,
                model_provider=provenance["model_provider"],
                model=provenance["model"],
                started_at=started_at,
                completed_at=_now_iso(now),
                status=status,
                spec_version=provenance.get("spec_version"),
            )
        return RunOutcome(result=result, run_record=run_record, exit_code=EXIT_CODES[status])

    try:
        check_request_preconditions(request)
        prepared = prepare_workspace(request)
        work_dir = prepared.paths.work_dir

        existing = _read_json_if_present(work_dir / "spec-result.json")
        if existing and existing.get("runId") == request.run_id:
            log(
                "info",
                "run.idempotent_replay",
                "Returning the existing terminal result for this runId.",
                runId=request.run_id,
                status=existing.get("status"),
            )
            status = existing["status"]
            return RunOutcome(result=_result_from_json(existing), run_record=None, exit_code=EXIT_CODES[status])
        prior_spec_version = (
            existing.get("specVersion", 1) if existing and existing.get("status") == "spec_ready" else 0
        )

        intent = read_intent_file(prepared.intent_path)
        verify_frozen_intent(request, intent, prepared.frozen_artifact_sha256)

        facts = inspect_repository(prepared.paths.root, cfg.inspection)
        gen = generator or create_generator(provider=cfg.provider, model=cfg.model)

        generated = _with_timeout(
            lambda cancel: gen.generate(
                SpecGenerationInput(
                    work_item=request.work_item,
                    product_id=request.product_id,
                    intent=intent,
                    repo_facts=facts,
                    repo_root=str(prepared.paths.root),
                    cancel=cancel,
                )
            ),
            cfg.generation_timeout_ms,
        )

        provenance: dict[str, Any] = {
            "model_provider": generated.model_provider,
            "model": generated.model,
            "base_commit": prepared.head_commit,
        }

        if generated.human_decisions:
            outcome = finish(
                "needs_decision",
                f"A material decision must be resolved before {request.work_item} can be specified.",
                human_decisions=generated.human_decisions,
                non_blocking_concerns=generated.non_blocking_concerns,
                frozen_artifact_sha256=prepared.frozen_artifact_sha256,
                provenance=provenance,
            )
            _persist_run_record(work_dir, outcome.run_record)
            return outcome

        spec_version = prior_spec_version + 1
        frontmatter = SpecFrontmatter(
            work_item=request.work_item,
            product_id=request.product_id,
            intent_commit=request.intent.commit,
            frozen_artifact_sha256=prepared.frozen_artifact_sha256,
            intent_content_sha256=request.intent.content_sha256,
            base_commit=prepared.head_commit,
            spec_version=spec_version,
        )
        spec_markdown = assemble_spec(generated.spec_body, frontmatter)
        check = validate_spec(spec_markdown)
        if not check.ok:
            concerns = [
                *(f"spec.md is missing required section: {s}" for s in check.missing_sections),
                *(
                    f"section '{s}' is marked not relevant without a rationale"
                    for s in check.not_relevant_without_rationale
                ),
                *(
                    f"section '{s}' contains an unresolved TODO/decision marker"
                    for s in check.unresolved_markers
                ),
                *(["functional requirements lack observable acceptance criteria"] if check.criteria_without_observability else []),
            ]
            outcome = finish(
                "failed",
                f"The generated specification for {request.work_item} did not meet the structural contract.",
                blocking_concerns=concerns,
                frozen_artifact_sha256=prepared.frozen_artifact_sha256,
                provenance={**provenance, "spec_version": spec_version},
            )
            _persist_run_record(work_dir, outcome.run_record)
            return outcome

        (work_dir / "spec.md").write_text(spec_markdown, encoding="utf-8")
        run_record = build_run_record(
            request=request,
            base_commit=prepared.head_commit,
            frozen_artifact_sha256=prepared.frozen_artifact_sha256,
            model_provider=generated.model_provider,
            model=generated.model,
            started_at=started_at,
            completed_at=_now_iso(now),
            status="spec_ready",
            spec_version=spec_version,
        )
        _persist_run_record(work_dir, run_record)

        spec_commit = git.stage_and_commit(
            prepared.paths.root,
            [prepared.paths.intent_rel, prepared.paths.spec_rel, prepared.paths.run_rel],
            f"spec({request.work_item}): spec v{spec_version} ready for Design Review [runId {request.run_id}]",
        )

        non_blocking = list(generated.non_blocking_concerns)
        if facts.limit_hit:
            non_blocking.append(f"repository inspection bound '{facts.limit_hit}' was hit; not fully enumerated")

        result = build_result(
            request=request,
            status="spec_ready",
            summary=f"spec.md v{spec_version} for {request.work_item} is committed and ready for Design Review.",
            frozen_artifact_sha256=prepared.frozen_artifact_sha256,
            spec_commit=spec_commit,
            spec_path=prepared.paths.spec_rel,
            spec_version=spec_version,
            non_blocking_concerns=non_blocking,
        )
        (work_dir / "spec-result.json").write_text(json.dumps(result.to_json(), indent=2), encoding="utf-8")

        log("info", "run.completed", "Spec & Design run completed.", runId=request.run_id, status=result.status)
        return RunOutcome(result=result, run_record=run_record, exit_code=0)

    except PreconditionError as error:
        log(
            "warn",
            "run.precondition_failed",
            "A precondition prevented specification.",
            runId=request.run_id,
            code=error.code,
            status=error.status,
        )
        if error.status == "needs_decision":
            return finish(
                "needs_decision",
                error_message(error),
                human_decisions=[
                    HumanDecision(
                        question=error.message,
                        impact="Blocks Spec & Design until resolved by the intent owner.",
                        minimum_authority="Product owner (via the Intent Creation Skill)",
                    )
                ],
            )
        return finish("blocked", error_message(error), blocking_concerns=[f"{error.code}: {error.message}"])
    except Exception as error:  # noqa: BLE001 - fail closed, never leak a stack trace to the Conductor
        log("error", "run.failed", "Spec & Design run failed unexpectedly.", runId=request.run_id, error=error_message(error))
        return finish(
            "failed",
            f"Unexpected failure during Spec & Design for {request.work_item}.",
            blocking_concerns=[error_message(error)],
        )


def _persist_run_record(work_dir: Path, record: SpecRunRecord | None) -> None:
    if record is None:
        return
    (work_dir / "spec-run.json").write_text(json.dumps(record.to_json(), indent=2), encoding="utf-8")


def _result_from_json(data: dict[str, Any]) -> SpecResult:
    return SpecResult(
        run_id=data["runId"],
        work_item=data["workItem"],
        status=data["status"],
        summary=data["summary"],
        branch=data["branch"],
        workspace=data["workspace"],
        intent_commit=data["intentCommit"],
        frozen_artifact_sha256=data["frozenArtifactSha256"],
        intent_content_sha256=data["intentContentSha256"],
        blocking_concerns=list(data.get("blockingConcerns", [])),
        non_blocking_concerns=list(data.get("nonBlockingConcerns", [])),
        human_decisions=[
            HumanDecision(
                question=d["question"],
                impact=d["impact"],
                minimum_authority=d["minimumAuthority"],
                options=d.get("options"),
            )
            for d in data.get("humanDecisions", [])
        ],
        spec_commit=data.get("specCommit"),
        spec_path=data.get("specPath"),
        spec_version=data.get("specVersion"),
    )
