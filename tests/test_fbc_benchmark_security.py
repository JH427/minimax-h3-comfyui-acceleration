import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_nodes"
    / "ComfyUI-MiniMaxH3-FirstBlockCache"
    / "benchmark"
    / "run_benchmark.py"
)
SPEC = importlib.util.spec_from_file_location("fbc_run_benchmark", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_output_path_stays_under_configured_root(tmp_path):
    result = MODULE.safe_output_path(tmp_path, "video/results", "render.mp4")

    assert result == (tmp_path / "video/results/render.mp4").resolve()


@pytest.mark.parametrize(
    ("subfolder", "filename"),
    [
        ("../outside", "render.mp4"),
        ("video", "../../outside.mp4"),
        ("video", "/etc/passwd"),
    ],
)
def test_output_path_rejects_absolute_and_traversing_history_values(
    tmp_path, subfolder, filename
):
    with pytest.raises(ValueError, match="outside COMFY_OUTPUT"):
        MODULE.safe_output_path(tmp_path, subfolder, filename)


def test_output_collection_requires_explicit_comfy_output(monkeypatch):
    monkeypatch.setattr(MODULE, "COMFY_OUTPUT", None)

    with pytest.raises(RuntimeError, match="COMFY_OUTPUT"):
        MODULE.output_files({"outputs": {}})
