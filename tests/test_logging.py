from spec_design_agent.logging_ import error_message, redact


def test_redacts_anthropic_and_generic_keys():
    assert redact("key sk-ant-abc123DEF_-xyz here") == "key [REDACTED_ANTHROPIC_KEY] here"
    assert redact("key sk-proj-abc123 here") == "key [REDACTED_API_KEY] here"


def test_redacts_github_tokens_and_bearer():
    assert redact("token ghp_ABCdef123456") == "token [REDACTED_GITHUB_TOKEN]"
    assert redact("Authorization: Bearer abc.def.ghi") == "Authorization: Bearer [REDACTED]"


def test_redacts_credentials_in_clone_urls():
    assert redact("https://user:s3cr3t@github.com/org/repo.git") == "https://[REDACTED]@github.com/org/repo.git"


def test_error_message_unwraps_and_redacts():
    assert error_message(RuntimeError("failed with sk-ant-secret_value")) == "failed with [REDACTED_ANTHROPIC_KEY]"


def test_leaves_clean_text_untouched():
    assert redact("nothing sensitive here") == "nothing sensitive here"
