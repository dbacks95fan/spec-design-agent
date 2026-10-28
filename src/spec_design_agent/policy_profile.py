# Copyright (c) 2026 DPSystems, LLC.
# ABOUTME: Parses the frozen policy profile's identity and bounded control table.

from __future__ import annotations

import re
from dataclasses import dataclass

from .types import PreconditionError, SpecRequest

_IDENTITY = re.compile(r"^\s*(Profile ID|Version):\s*(.*?)\s*$", re.IGNORECASE | re.MULTILINE)
_PLACEHOLDER = re.compile(r"^<.*>$")


@dataclass(frozen=True)
class PolicyControl:
    control_id: str
    required_action: str
    evidence_expected: str

    def to_json(self) -> dict[str, str]:
        return {
            "control_id": self.control_id,
            "required_action": self.required_action,
            "evidence_expected": self.evidence_expected,
        }


@dataclass(frozen=True)
class ParsedPolicyProfile:
    profile_id: str
    version: str
    raw: str
    controls: tuple[PolicyControl, ...]


def parse_policy_profile(raw: str, request: SpecRequest) -> ParsedPolicyProfile:
    values = {key.lower(): value for key, value in _IDENTITY.findall(raw)}
    profile_id, version = values.get("profile id", "").strip(), values.get("version", "").strip()
    if not profile_id or not version or _PLACEHOLDER.match(profile_id) or _PLACEHOLDER.match(version):
        raise PreconditionError("blocked", "POLICY_PROFILE_IDENTITY_MISSING", "Frozen policy profile has no completed Profile ID and Version")
    if (profile_id, version) != (request.policy_profile.profile_id, request.policy_profile.version):
        raise PreconditionError("blocked", "POLICY_PROFILE_IDENTITY_MISMATCH", "Frozen policy-profile ID or version does not match the Prioritized freeze record")

    controls: list[PolicyControl] = []
    for line in raw.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4 or cells[0].lower() in {"control id", "---"} or set("".join(cells[0])) == {"-"}:
            continue
        control_id, action, evidence = cells[:3]
        if not control_id or _PLACEHOLDER.match(control_id) or _PLACEHOLDER.match(action):
            continue
        controls.append(PolicyControl(control_id, action, evidence))
    return ParsedPolicyProfile(profile_id, version, raw, tuple(controls))
