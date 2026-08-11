import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
from check_public_content import (  # noqa: E402, I001
    artifact_problem,
    find_text_problems,
    public_files,
)


GRID = Path(
    "custom_nodes/ComfyUI-MiniMax-H3-Turbo/h3_silu_temb_grid.safetensors"
)


def test_public_gate_scans_source_archive_without_git_metadata(tmp_path):
    (tmp_path / "README.md").write_text("safe", encoding="utf-8")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "tool.py").write_text("safe", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "ignored.pyc").write_bytes(b"ignored")

    assert public_files(tmp_path) == [Path("README.md"), Path("nested/tool.py")]


def test_public_gate_detects_generic_private_and_secret_material():
    text = "\n".join(
        (
            "contact person" + "@" + "example.com",
            "endpoint http://" + "10." + "0.0.7:8188",
            "file /" + "home/alice/private.mov",
            "api_" + 'key = "not-a-real-but-leaked-key"',
        )
    )

    problems = find_text_problems(Path("notes.txt"), text)

    assert any("email" in problem for problem in problems)
    assert any("private IP" in problem for problem in problems)
    assert any("home path" in problem for problem in problems)
    assert any("credential" in problem for problem in problems)


def test_public_gate_detects_common_credential_and_ipv6_formats():
    text = "\n".join(
        (
            "tok" + "en = unquoted-secret-value",
            "Author" + "ization: Bearer example-bearer-value",
            "-----BEGIN PRI" + "VATE KEY-----",
            "endpoint http://[fd" + "00::1]:8188",
        )
    )

    problems = find_text_problems(Path("config.txt"), text)

    assert any("credential" in problem for problem in problems)
    assert any("private key" in problem for problem in problems)
    assert any("private IP" in problem for problem in problems)


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
def test_public_gate_detects_each_provider_prefixed_credential(name):
    problems = find_text_problems(Path(".env"), f"{name}=example-secret-value")

    assert any("credential" in problem for problem in problems), name


def test_public_gate_allows_only_the_audited_runtime_tensor():
    assert not find_text_problems(
        Path("pyproject.toml"), 'classifiers = ["Programming Language :: Python :: 3.10"]'
    )
    assert artifact_problem(GRID) is None
    assert artifact_problem(Path("models/model.safetensors")) is not None
    assert artifact_problem(Path("output/frame.png")) is not None
    assert artifact_problem(Path("output/audio.wav")) is not None
    assert artifact_problem(Path("output/video.webm")) is not None
