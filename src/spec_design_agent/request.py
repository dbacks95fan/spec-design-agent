# ABOUTME: Parses and validates the Conductor work request before any artifact work begins.
# ABOUTME: Rejects incompatible invocation versions and inconsistent freeze identity before work begins.

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from .schema import validate
from .types import (
    SUPPORTED_REQUEST_VERSION,
    PreconditionError,
    RequestValidationError,
    SpecRequest,
)


def validate_request_shape(value: Any) -> SpecRequest:
    """Structural validation only. Raises RequestValidationError (a usage error) on a shape problem."""
    errors = validate("spec-request.schema.json", value)
    if errors:
        raise RequestValidationError(errors)
    return SpecRequest.from_dict(value)


def check_request_preconditions(request: SpecRequest) -> None:
    """Semantic preconditions the Conductor must satisfy. Raises PreconditionError."""
    if request.request_version != SUPPORTED_REQUEST_VERSION:
        raise PreconditionError(
            "blocked",
            "UNSUPPORTED_REQUEST_VERSION",
            f"Request version {request.request_version} is not supported; "
            f"this agent implements version {SUPPORTED_REQUEST_VERSION}",
        )
    freeze = request.freeze_activation
    if request.stage != "spec_design":
        raise PreconditionError("blocked", "WRONG_STAGE", "This worker only accepts the spec_design stage")
    if (freeze.product_id, freeze.intent_id) != (request.product_id, request.work_item):
        raise PreconditionError("blocked", "FREEZE_IDENTITY_MISMATCH", "Freeze record identity does not match the invocation")
    profile_ref = request.policy_profile
    if not request.intent.path.endswith(f"{request.work_item}/intent.md"):
        raise PreconditionError("blocked", "INTENT_PATH_MISMATCH", "Frozen intent path does not identify this work item")
    if not profile_ref.path:
        raise PreconditionError("blocked", "POLICY_PROFILE_PATH_MISSING", "Frozen policy profile reference has no path")
    for path in [*request.read_paths, *request.write_paths]:
        normalized = PurePosixPath(path)
        if "\\" in path or normalized.is_absolute() or ".." in normalized.parts:
            raise PreconditionError("blocked", "INVALID_PATH_PERMISSION", "Invocation path permissions must be normalized repository-relative paths")
    if "." not in request.read_paths:
        raise PreconditionError("blocked", "READ_SCOPE_INSUFFICIENT", "Spec & Design requires read access to the assigned product repository")
    allowed_work_dir = f".agent/work/{request.work_item}"
    if request.write_paths != [allowed_work_dir]:
        raise PreconditionError("blocked", "WRITE_SCOPE_INVALID", "Invocation must grant write access only to the assigned .agent/work directory")
    # Cross-field consistency: branch and frozen-intent path must both name this work
    # item, so a mis-routed request cannot start work.
    if not request.target.branch.endswith(request.work_item):
        raise PreconditionError(
            "blocked",
            "BRANCH_MISMATCH",
            f"Target branch '{request.target.branch}' does not name work item '{request.work_item}'",
        )
    if freeze.intent_id != request.work_item:
        raise PreconditionError("blocked", "INTENT_ID_MISMATCH", "Frozen intent ID does not match the invocation work item")


def parse_request(value: Any) -> SpecRequest:
    """Shape + preconditions in one call (used by tests)."""
    request = validate_request_shape(value)
    check_request_preconditions(request)
    return request
