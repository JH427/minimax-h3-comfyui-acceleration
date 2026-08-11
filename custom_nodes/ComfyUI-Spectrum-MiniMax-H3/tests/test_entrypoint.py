from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def test_comfyui_directory_loader_resolves_bundled_package(tmp_path):
    repository = Path(__file__).resolve().parents[1]
    custom_node = tmp_path / "comfyui-spectrum-minimax-h3"
    bundled_package = custom_node / "comfyui_spectrum_h3"
    bundled_package.mkdir(parents=True)

    shutil.copy(repository / "__init__.py", custom_node / "__init__.py")
    shutil.copy(repository / "nodes.py", custom_node / "nodes.py")
    (bundled_package / "__init__.py").write_text("", encoding="utf-8")
    (bundled_package / "nodes.py").write_text(
        "class SpectrumApplyMiniMaxH3:\n"
        "    pass\n"
        "NODE_CLASS_MAPPINGS = {'SpectrumApplyMiniMaxH3': SpectrumApplyMiniMaxH3}\n"
        "NODE_DISPLAY_NAME_MAPPINGS = {'SpectrumApplyMiniMaxH3': 'Spectrum Apply MiniMax H3'}\n",
        encoding="utf-8",
    )

    loader_script = """
import importlib.util
import pathlib
import sys

module_path = pathlib.Path(sys.argv[1]).resolve()
module_name = str(module_path).replace('.', '_x_')
spec = importlib.util.spec_from_file_location(module_name, module_path / '__init__.py')
module = importlib.util.module_from_spec(spec)
sys.modules[module_name] = module
spec.loader.exec_module(module)
assert 'SpectrumApplyMiniMaxH3' in module.NODE_CLASS_MAPPINGS
"""
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, "-I", "-c", loader_script, str(custom_node)],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
