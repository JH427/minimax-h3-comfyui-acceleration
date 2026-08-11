import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_checked_in_api_examples_match_canonical_generator():
    result = subprocess.run(
        [sys.executable, "tools/generate_api_examples.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_checked_in_ui_examples_match_canonical_generator():
    result = subprocess.run(
        [sys.executable, "tools/generate_ui_examples.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
