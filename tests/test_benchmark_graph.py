import sys
from argparse import Namespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
from benchmark import (  # noqa: E402
    default_steps,
    prompt_graph,
    valid_frame_count,
    validate_http_url,
)


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


def test_server_url_allows_only_http_and_https():
    assert validate_http_url("http://127.0.0.1:8188") == "http://127.0.0.1:8188"
    assert validate_http_url("https://example.com/comfy") == "https://example.com/comfy"
    with pytest.raises(ValueError, match="HTTP or HTTPS"):
        validate_http_url("file:///tmp/history.json")
    with pytest.raises(ValueError, match="hostname"):
        validate_http_url("http:///missing-host")


def test_h3_frame_count_grid_validation():
    assert valid_frame_count(5)
    assert valid_frame_count(39)
    assert valid_frame_count(124)
    assert not valid_frame_count(0)
    assert not valid_frame_count(40)


def test_lane_specific_default_steps():
    assert default_steps("control") == 20
    assert default_steps("fbc-safe") == 20
    assert default_steps("spectrum") == 20
    assert default_steps("turbo") == 8


def test_control_keeps_native_model_and_sampler():
    graph = prompt_graph(make_args())
    assert graph["16"]["inputs"]["model"] == ["6", 0]
    assert graph["9"]["inputs"]["model"] == ["6", 0]
    assert graph["17"]["inputs"]["sampler_name"] == "res_multistep"


def test_fbc_safe_patches_model_for_guider_and_scheduler():
    graph = prompt_graph(make_args("fbc-safe"))
    assert graph["200"]["class_type"] == "ApplyMiniMaxH3FirstBlockCache"
    assert graph["200"]["inputs"]["mode"] == "H3 Safe — 0.08 / max 2"
    assert graph["200"]["inputs"]["temporal_guard"] is False
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
