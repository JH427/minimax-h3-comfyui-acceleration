import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
from sanitize_manifest import REDACTED, clean  # noqa: E402


def test_sanitizer_drops_sensitive_keys_case_insensitively():
    result = clean(
        {
            "Server": "http://" + "10." + "0.0.2:8188",
            "HostName": "private-box",
            "api_key": "secret-value",
            "config": {"prompt": "private client prompt", "seed": 9001},
        }
    )

    assert result == {"config": {"seed": 9001}}


def test_sanitizer_removes_common_token_key_variants():
    result = clean(
        {
            "apiKey": "value-one",
            "access_" + "token": "value-two",
            "github_" + "token": "value-three",
            "auth": "value-four",
            "safe_metric": 12.5,
        }
    )

    assert result == {"safe_metric": 12.5}


@pytest.mark.parametrize(
    "name",
    [
        "OPENAI_API_KEY",
        "openaiApiKey",
        "OpenAIApiKey",
        "AWS_SECRET_ACCESS_KEY",
        "awsSecretAccessKey",
        "AWSSecretAccessKey",
        "HF_TOKEN",
        "hfToken",
        "HFToken",
        "databasePassword",
        "myClientSecret",
    ],
)
def test_sanitizer_removes_each_provider_prefixed_credential_key(name):
    assert clean({name: "example-secret-value"}) == {}


@pytest.mark.parametrize(
    "name",
    [
        "OPENAI_API_KEY",
        "openaiApiKey",
        "OpenAIApiKey",
        "AWS_SECRET_ACCESS_KEY",
        "awsSecretAccessKey",
        "AWSSecretAccessKey",
        "HF_TOKEN",
        "hfToken",
        "HFToken",
        "databasePassword",
        "myClientSecret",
    ],
)
def test_sanitizer_redacts_each_provider_prefixed_inline_credential(name):
    assert clean(f"{name}=example-secret-value") == REDACTED


def test_sanitizer_redacts_credentials_private_keys_and_private_ipv6_in_strings():
    result = clean(
        {
            "header": "Author" + "ization: Bearer example-bearer-value",
            "assignment": "tok" + "en = unquoted-secret-value",
            "key_material": "-----BEGIN PRI" + "VATE KEY-----",
            "endpoint": "http://[fd" + "00::1]:8188",
        }
    )

    assert set(result.values()) == {REDACTED}


def test_sanitizer_redacts_sensitive_values_under_arbitrary_keys():
    result = clean(
        {
            "note": "/" + "home/alice/private.mov",
            "contact": "person" + "@" + "example.com",
            "endpoint": "http://" + "192." + "168.1.20:8188",
            "safe": "synthetic benchmark",
            "localhost": "http://127.0.0.1:8188",
            "classifier": "Programming Language :: Python :: 3.10",
        }
    )

    assert result["note"] == REDACTED
    assert result["contact"] == REDACTED
    assert result["endpoint"] == REDACTED
    assert result["safe"] == "synthetic benchmark"
    assert result["localhost"] == "http://127.0.0.1:8188"
    assert result["classifier"] == "Programming Language :: Python :: 3.10"
