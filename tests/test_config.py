import re
from pathlib import Path

import pytest
import yaml

from spec_design_agent.config import load_config

ROOT = Path(__file__).resolve().parents[1]


def test_load_config_defaults(monkeypatch):
    for key in list(__import__("os").environ):
        if key.startswith("SPEC_AGENT_"):
            monkeypatch.delenv(key, raising=False)
    config = load_config()
    assert config.provider == "claude"
    assert config.generation_timeout_ms == 600000
    assert config.inspection.max_depth == 6


def test_load_config_reads_env_overrides(monkeypatch):
    monkeypatch.setenv("SPEC_AGENT_PROVIDER", "mock")
    monkeypatch.setenv("SPEC_AGENT_TIMEOUT_MS", "1234")
    monkeypatch.setenv("SPEC_AGENT_MAX_FILES", "10")
    config = load_config()
    assert config.provider == "mock"
    assert config.generation_timeout_ms == 1234
    assert config.inspection.max_files == 10


def test_load_config_rejects_non_positive_env(monkeypatch):
    monkeypatch.setenv("SPEC_AGENT_TIMEOUT_MS", "-5")
    with pytest.raises(ValueError, match="must be a positive number"):
        load_config()


def test_explicit_overrides_win_over_environment(monkeypatch):
    monkeypatch.setenv("SPEC_AGENT_PROVIDER", "codex")
    assert load_config(provider="mock").provider == "mock"


def test_compose_runs_agent_as_one_shot_job_with_configurable_provider():
    compose = yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))
    service = compose["services"]["spec-design-agent"]
    assert service["restart"] == "no"
    assert "SPEC_AGENT_PROVIDER" in service["environment"]


def test_dockerfile_entrypoint_is_the_cli_and_image_is_non_root():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert re.search(r'ENTRYPOINT \["python", "-m", "spec_design_agent"\]', dockerfile)
    assert "USER specagent" in dockerfile


def test_env_example_documents_provider_choices():
    env = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "SPEC_AGENT_PROVIDER=claude" in env
    assert "claude | codex | mock" in env
