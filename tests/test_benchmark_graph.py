import sys
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
from benchmark import prompt_graph  # noqa: E402


def make_args(accel="control", steps=20):
    return Namespace(
        model="minimax_h3_fl2va_pruned_int8_convrot.safetensors",
        encoder="qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
        encoder_device="default",
        width=608,
        height=352,
        length=39,
        steps=steps,
        seed=9001,
        prefix="H3_accel_test",
        prompt="synthetic test prompt",
        accel=accel,
        turbo_lora="minimax_h3_turbo_v4_step600_ema.safetensors",
        label="test",
        client_id="test-client",
    )


def test_control_keeps_native_model_and_sampler():
    graph = prompt_graph(make_args())
    assert graph["16"]["inputs"]["model"] == ["6", 0]
    assert graph["9"]["inputs"]["model"] == ["6", 0]
    assert graph["17"]["inputs"]["sampler_name"] == "res_multistep"


def test_fbc_safe_patches_model_for_guider_and_scheduler():
    graph = prompt_graph(make_args("fbc-safe"))
    assert graph["200"]["class_type"] == "ApplyMiniMaxH3FirstBlockCache"
    assert graph["16"]["inputs"]["model"] == ["200", 0]
    assert graph["9"]["inputs"]["model"] == ["200", 0]


def test_turbo_uses_dedicated_sampler():
    graph = prompt_graph(make_args("turbo", 8))
    assert graph["201"]["class_type"] == "MiniMaxH3TurboLoRA"
    assert graph["202"]["class_type"] == "MiniMaxH3TurboSampler"
    assert graph["14"]["inputs"]["sampler"] == ["202", 0]
    assert graph["9"]["inputs"]["steps"] == 8


def test_spectrum_uses_audio_safe_defaults():
    graph = prompt_graph(make_args("spectrum"))
    assert graph["203"]["class_type"] == "SpectrumApplyMiniMaxH3"
    assert graph["203"]["inputs"]["offline_smoothing_replay"] is True
    assert graph["203"]["inputs"]["audio_blend_weight"] == 0.0
    assert graph["16"]["inputs"]["model"] == ["203", 0]
