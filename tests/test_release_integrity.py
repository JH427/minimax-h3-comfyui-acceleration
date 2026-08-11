import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
TURBO_GRID = (
    ROOT
    / "custom_nodes"
    / "ComfyUI-MiniMax-H3-Turbo"
    / "h3_silu_temb_grid.safetensors"
)
TURBO_GRID_SHA256 = "30eb3c2cc7fb6b470d9717ff840d359313ac27cd64b705e32da1baa10f72d6a8"


def test_workflow_sources_are_attributed_by_origin_and_license():
    manifest = json.loads((ROOT / "vendored-components.json").read_text())
    sources = {entry["name"]: entry for entry in manifest["workflow_sources"]}

    native = sources["Comfy Org MiniMax H3 native template"]
    assert native["license"] == "MIT"
    assert native["commit"] == "5c75d9f137bb27706a70dd337dac6249b2e51ded"
    assert native["sha256"] == "31ab33fdb053a7834cc866bd7aa08b887518fc656e4a796c89779c6b5e1786e6"
    assert native["files"] == ["workflows/h3-native-t2v.json"]

    turbo = sources["MiniMax H3 Turbo example workflow"]
    assert turbo["license"] == "Apache-2.0"
    assert set(turbo["derived_files"]) == {
        "workflows/h3-turbo8-t2v.json",
        "workflows/h3-spectrum-t2v.json",
        "workflows/h3-fbc-safe-t2v.json",
    }
    assert (ROOT / "LICENSE-COMFY-WORKFLOW-TEMPLATES-MIT.txt").is_file()


def test_spectrum_documentation_requires_a_compatible_comfyui_release():
    for relative in ("README.md", "docs/installation.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "0.31.0" in text
        assert "0.30.0 or later" not in text


def test_privacy_guide_points_to_existing_provenance_manifest():
    text = (ROOT / "docs/privacy.md").read_text(encoding="utf-8")
    assert "vendored-components.json" in text
    assert "VENDORED_COMPONENTS.md" not in text


def test_turbo_pruned_runtime_grid_is_present_and_verified():
    assert TURBO_GRID.is_file()
    assert hashlib.sha256(TURBO_GRID.read_bytes()).hexdigest() == TURBO_GRID_SHA256


def test_root_does_not_advertise_a_python_wheel():
    assert not (ROOT / "pyproject.toml").exists()
    assert (ROOT / "pytest.ini").read_text(encoding="utf-8").strip()
    assert (ROOT / "ruff.toml").read_text(encoding="utf-8").strip()


def test_accelerator_ui_workflows_cover_spectrum_and_fbc():
    expected = {
        "h3-fbc-safe-t2v.json": "ApplyMiniMaxH3FirstBlockCache",
        "h3-spectrum-t2v.json": "SpectrumApplyMiniMaxH3",
    }
    for filename, accelerator_type in expected.items():
        workflow = json.loads((ROOT / "workflows" / filename).read_text())
        nodes = {node["type"]: node for node in workflow["nodes"]}
        assert accelerator_type in nodes
        assert nodes["BasicScheduler"]["widgets_values"][1] == 20
        assert nodes["KSamplerSelect"]["widgets_values"][0] == "res_multistep"
        assert nodes["UNETLoader"]["widgets_values"][0] == (
            "minimax_h3_fl2va_pruned_int8_convrot.safetensors"
        )


def test_vendored_turbo_example_matches_promoted_ui_workflow():
    promoted = json.loads((ROOT / "workflows" / "h3-turbo8-t2v.json").read_text())
    vendored = json.loads(
        (
            ROOT
            / "custom_nodes"
            / "ComfyUI-MiniMax-H3-Turbo"
            / "example_workflows"
            / "minimax_h3_t2v_turbo.json"
        ).read_text()
    )
    assert vendored == promoted


def test_turbo8_ui_workflow_uses_promoted_models_and_eight_steps():
    workflow = json.loads((ROOT / "workflows" / "h3-turbo8-t2v.json").read_text())
    nodes = {node["type"]: node for node in workflow["nodes"]}

    assert nodes["BasicScheduler"]["widgets_values"][1] == 8
    assert nodes["UNETLoader"]["widgets_values"][0] == (
        "minimax_h3_fl2va_pruned_int8_convrot.safetensors"
    )
    assert nodes["CLIPLoader"]["widgets_values"][0] == (
        "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
    )
    assert nodes["MiniMaxH3TurboLoRA"]["widgets_values"] == [
        "minimax_h3_turbo_v4_step600_ema.safetensors",
        1,
        False,
    ]
