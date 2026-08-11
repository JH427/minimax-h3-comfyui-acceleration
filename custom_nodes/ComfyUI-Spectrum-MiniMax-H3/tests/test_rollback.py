from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest
import torch

from comfyui_spectrum_h3.config import SpectrumH3Config
from comfyui_spectrum_h3.rollback import run_selective_rollback_euler
from comfyui_spectrum_h3.runtime import SpectrumH3Runtime


TOPOLOGY = (("tiny", 1),)
LABELS = ((0, "positive"),)


class _ModelSampling:
    sigma_max = 1.0

    @staticmethod
    def noise_scaling(_sigma, noise, _latent, _max_denoise):
        return noise.clone()

    @staticmethod
    def inverse_noise_scaling(_sigma, samples):
        return samples


class _FakeSampler:
    inpaint_options = {}

    @staticmethod
    def max_denoise(_model_wrap, _sigmas):
        return False


def _install_fake_comfy(monkeypatch, model_k_type):
    comfy = ModuleType("comfy")
    k_diffusion = ModuleType("comfy.k_diffusion")
    sampling = ModuleType("comfy.k_diffusion.sampling")
    sampling.trange = lambda count, disable=None: range(count)
    sampling.to_d = lambda x, sigma, denoised: (x - denoised) / sigma
    model_management = ModuleType("comfy.model_management")
    model_management.throw_exception_if_processing_interrupted = lambda: None
    samplers = ModuleType("comfy.samplers")
    samplers.KSamplerX0Inpaint = model_k_type
    comfy.k_diffusion = k_diffusion
    comfy.model_management = model_management
    comfy.samplers = samplers
    k_diffusion.sampling = sampling
    monkeypatch.setitem(sys.modules, "comfy", comfy)
    monkeypatch.setitem(sys.modules, "comfy.k_diffusion", k_diffusion)
    monkeypatch.setitem(sys.modules, "comfy.k_diffusion.sampling", sampling)
    monkeypatch.setitem(sys.modules, "comfy.model_management", model_management)
    monkeypatch.setitem(sys.modules, "comfy.samplers", samplers)


def _run(
    monkeypatch,
    *,
    trigger: bool,
    residual_trigger: bool = False,
    residual_shadow: float = 0.5,
    initial_rollbacks: int = 0,
):
    runtime = SpectrumH3Runtime(
        SpectrumH3Config(
            degree=1,
            max_history=4,
            warmup_steps=2,
            tail_actual_steps=0,
            window_size=2.0,
            flex_window=0.0,
            bootstrap_first_forecast=False,
            selective_rollback_correction=True,
            offline_smoothing_replay=False,
            audio_blend_weight=0.5,
        )
    )
    sigmas = torch.tensor([1.0, 0.75, 0.5, 0.25, 0.0])
    run_id = runtime.start_run(
        sigmas,
        "sample_euler",
        supported_sampler=True,
        max_consecutive_forecasts=1,
        min_actual_steps_after_forecast=1,
    )
    runtime.stats.rollback_count = initial_rollbacks
    calls = []

    class FakeModelK:
        def __init__(self, model_wrap, _sigmas):
            self.model_wrap = model_wrap

        def __call__(self, x, sigma, **_extra_args):
            decision = runtime.begin_step(sigma)
            call_id, actual = runtime.begin_model_call(
                decision["run_id"],
                decision["step_id"],
                topology=TOPOLOGY,
                labels=LABELS,
                expected_shape=(1, 1, 1),
            )
            probe = None
            if actual and residual_trigger:
                probe = runtime.prepare_residual_probe(
                    decision["run_id"],
                    decision["step_id"],
                    call_id,
                    device=torch.device("cpu"),
                    dtype=torch.float32,
                )
            if actual:
                actual_feature = torch.full(
                    (1, 1, 1),
                    float(decision["step_id"]),
                )
                runtime.observe_actual(
                    decision["run_id"],
                    decision["step_id"],
                    call_id,
                    actual_feature,
                )
                if probe is not None:
                    runtime.record_residual_measurement(
                        decision["run_id"],
                        decision["step_id"],
                        call_id,
                        probe,
                        actual_feature=actual_feature,
                        actual_output=[torch.tensor([2.0]), torch.tensor([2.0])],
                        shadow_output=[
                            torch.tensor([residual_shadow]),
                            torch.tensor([residual_shadow]),
                        ],
                        hold_output=[torch.tensor([1.0]), torch.tensor([1.0])],
                    )
            else:
                assert runtime.predict(
                    decision["run_id"],
                    decision["step_id"],
                    call_id,
                    device=torch.device("cpu"),
                    dtype=torch.float32,
                ) is not None
            runtime.finalize_step(decision["run_id"], decision["step_id"])
            if (
                trigger
                and decision["step_id"] == 3
                and actual
                and not runtime._rollback_replay_active
            ):
                runtime._rollback_requested = True
            calls.append((decision["step_id"], actual, float(x.item())))
            return x * 0.5 if actual else x + 2.0

    _install_fake_comfy(monkeypatch, FakeModelK)
    callbacks = []
    model_wrap = SimpleNamespace(
        inner_model=SimpleNamespace(model_sampling=_ModelSampling())
    )
    result = run_selective_rollback_euler(
        _FakeSampler(),
        runtime,
        model_wrap,
        sigmas,
        {"seed": 7},
        lambda index, denoised, x, total: callbacks.append(
            (index, float(denoised.item()), float(x.item()), total)
        ),
        torch.ones(1),
        torch.zeros(1),
        None,
        True,
    )
    return runtime, run_id, result, calls, callbacks


def test_selective_rollback_replays_forecast_and_anchor_at_corrected_latents(monkeypatch):
    runtime, run_id, result, calls, callbacks = _run(monkeypatch, trigger=True)
    assert [step_id for step_id, _actual, _x in calls] == [0, 1, 2, 3, 2, 3]
    original_anchor_x = calls[3][2]
    corrected_anchor_x = calls[5][2]
    assert corrected_anchor_x != pytest.approx(original_anchor_x)
    assert corrected_anchor_x == pytest.approx(0.546875)
    assert float(result.item()) == pytest.approx(0.2734375)
    assert [entry[0] for entry in callbacks] == [0, 1, 2, 3]
    assert runtime.stats.rollback_count == 1
    assert runtime.stats.speculative_forecast_calls == 1
    assert runtime.stats.discarded_actual_calls == 1
    assert runtime.stats.replayed_transformer_calls == 2
    assert runtime.stats.actual_transformer_calls == 5
    runtime.end_run(run_id)



def test_selective_rollback_no_trigger_matches_the_unreplayed_euler_path(monkeypatch):
    runtime, run_id, result, calls, callbacks = _run(monkeypatch, trigger=False)
    assert [step_id for step_id, _actual, _x in calls] == [0, 1, 2, 3]
    assert float(result.item()) == pytest.approx(0.8645833333)
    assert [entry[0] for entry in callbacks] == [0, 1, 2, 3]
    assert runtime.stats.rollback_count == 0
    assert runtime.stats.replayed_transformer_calls == 0
    runtime.end_run(run_id)


def test_selective_rollback_is_triggered_by_recorded_residual_policy(monkeypatch):
    runtime, run_id, _result, calls, _callbacks = _run(
        monkeypatch,
        trigger=False,
        residual_trigger=True,
    )
    assert [step_id for step_id, _actual, _x in calls] == [0, 1, 2, 3, 2, 3]
    assert runtime.stats.residual_anchors == 1
    assert runtime.stats.residual_max_score == pytest.approx(1.5)
    assert runtime.stats.rollback_count == 1
    runtime.end_run(run_id)


def test_selective_rollback_accepts_score_below_threshold(monkeypatch):
    runtime, run_id, _result, calls, _callbacks = _run(
        monkeypatch,
        trigger=False,
        residual_trigger=True,
        residual_shadow=0.6,
    )
    assert [step_id for step_id, _actual, _x in calls] == [0, 1, 2, 3]
    assert runtime.stats.residual_policy_max_score == pytest.approx(1.4)
    assert runtime.stats.rollback_suppressed_threshold == 1
    assert runtime.stats.rollback_count == 0
    runtime.end_run(run_id)


def test_selective_rollback_skips_probe_after_three_corrections(monkeypatch):
    runtime, run_id, _result, calls, _callbacks = _run(
        monkeypatch,
        trigger=False,
        residual_trigger=True,
        initial_rollbacks=3,
    )
    assert [step_id for step_id, _actual, _x in calls] == [0, 1, 2, 3]
    assert runtime.stats.residual_anchors == 0
    assert runtime.stats.rollback_suppressed_budget == 1
    assert runtime.stats.rollback_count == 3
    runtime.end_run(run_id)
