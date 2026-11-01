import os

import pytest

from spec_design_agent import git


@pytest.fixture(autouse=True)
def reset_cached_app_token():
    git._APP_TOKEN = None
    git._APP_TOKEN_CAPTURED = False
    yield
    git._APP_TOKEN = None
    git._APP_TOKEN_CAPTURED = False


def test_git_uses_only_the_spec_agent_installation_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "personal-token-must-not-be-used")
    monkeypatch.setenv("SPEC_AGENT_GITHUB_TOKEN", "short-lived-installation-token")

    env = git._git_env()

    assert "GITHUB_TOKEN" not in env
    assert "SPEC_AGENT_GITHUB_TOKEN" not in os.environ
    assert env["SPEC_AGENT_GITHUB_TOKEN"] == "short-lived-installation-token"
    assert env["GIT_CONFIG_COUNT"] == "3"
    assert env["GIT_CONFIG_KEY_0"] == "credential.https://github.com.helper"
    assert env["GIT_CONFIG_VALUE_0"] == ""
    assert "$SPEC_AGENT_GITHUB_TOKEN" in env["GIT_CONFIG_VALUE_1"]
    assert env["GIT_CONFIG_VALUE_1"].startswith("!f()")
    assert env["GIT_CONFIG_KEY_2"] == "credential.https://github.com.useHttpPath"


def test_git_is_never_handed_a_model_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-must-not-reach-git")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-must-not-reach-git")

    env = git._git_env()

    assert "OPENAI_API_KEY" not in env
    assert "ANTHROPIC_API_KEY" not in env
    assert os.environ["OPENAI_API_KEY"] == "sk-openai-must-not-reach-git", "the generator still needs it"


def test_github_clone_requires_installation_token_not_generic_token(monkeypatch, tmp_path):
    monkeypatch.delenv("SPEC_AGENT_GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "personal-token-must-not-be-used")

    with pytest.raises(RuntimeError, match="SPEC_AGENT_GITHUB_TOKEN"):
        git.clone_repository("https://github.com/example/product.git", tmp_path / "product")
