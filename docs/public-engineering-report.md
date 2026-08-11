# MiniMax H3 on AMD ROCm
## Public engineering and optimization report

Status: public, sanitized summary
Scope: MiniMax H3 local video/audio generation through ComfyUI on AMD ROCm
Audience: users and developers evaluating the acceleration pack

## Executive summary

This project began as a local MiniMax H3 bring-up and performance investigation
on an AMD Strix Halo system. The work produced three useful outcomes:

1. A verified native H3 video-and-audio generation lane.
2. A diagnosis of the major runtime cost at the tested resolution.
3. Optional work-reduction accelerators that materially reduce end-to-end render
time while remaining opt-in.

The central conclusion is:

> At the tested 608x352 resolution, the largest practical speedups came from
> executing fewer expensive H3 transformer evaluations, not from continuing
> generic attention-backend or small-kernel experiments.

The native lane remains the control. The accelerators are optional and must be
selected in the workflow.

## Project boundaries

This public repository contains source code, workflows, tests, documentation,
and sanitized benchmark summaries. It does not contain model weights, private
prompts, generated media, private logs, local machine paths, private network
addresses, credentials, or personal data.

The measurements below are hardware- and configuration-specific. They are not
vendor guarantees and should not be treated as universal performance claims.

## System and workload

The reference campaign used:

- AMD Strix Halo unified-memory system with Radeon 8060S / gfx1151.
- ROCm 7.2.
- PyTorch 2.13.0 with ROCm support.
- ComfyUI 0.30.0-era native MiniMax H3 integration.
- 608x352 output.
- 24 frames per second.
- Native RES multistep sampling.
- 20 sampling steps unless a Turbo lane explicitly used fewer steps.
- Generated video plus stereo audio.
- Same prompt and seed for matched lane comparisons.

H3 frame counts follow the model's supported frame-grid convention. The main
comparison lengths were 39 frames (1.625 seconds) and 124 frames (5.167 seconds).

## 1. Bring-up and native control

### Native text-to-video/audio

The official native workflow completed a short 608x352 smoke run with valid H.264
video and AAC 32 kHz stereo audio. This established that the machine was running
real H3 inference rather than only loading a graph or producing a synthetic
kernel result.

### Image-conditioning repair

Image-conditioned H3 initially failed in the Qwen vision patch-embedding path
on an AMD ROCm/MIOpen 3D-convolution operation. The local experimental repair
replaced only that patch-sized convolution with an equivalent flattened linear
projection while preserving the surrounding weight-casting and offload hooks.

The repair was validated with a short image-conditioned H3 job that produced a
valid H.264/AAC result and a focused regression test. It was kept separate from
the public acceleration pack because it modifies ComfyUI core behavior and needs
to track upstream compatibility carefully.

### Model and precision choices

The initial comparison established the native INT8 ConvRot transformer with the
GPU-resident quantized text encoder as the sensible control for this system.
BF16 was slower at the tested shape. Moving the text encoder to CPU was also
slower. These choices were therefore treated as control decisions, not further
optimization targets.

## 2. Backend and exact-math experiments

Several lower-level paths were tested or investigated before changing the
algorithmic workload:

- Default PyTorch attention versus explicit alternative attention settings.
- AOTriton environment variants.
- CPU versus GPU text-encoder placement.
- BF16 versus INT8/ConvRot model paths.
- Split-attention experiments.
- Dispatch and tensor-layout tracing.
- Exact H3 matrix-shape profiling.
- Candidate INT8 WMMA tile and kernel configurations.
- VAE decode timing.
- AdaLN projection timing.

### What the measurements showed

At approximately 2,688 packed rows, a representative first H3 block spent more
time in QKV and MLP projections, normalization/RoPE, and related block work than
in SDPA alone. Split attention made the tested attention site substantially
slower. Dispatch tracing confirmed that the quantized QKV and MLP paths reached
the intended native INT8 kernel rather than silently falling back to BF16.

The exact-math kernel work was valuable negative evidence. It localized a real
kernel-level bottleneck and identified an aspect-ratio heuristic that was not
obviously matched to H3's very wide matrices, but no candidate crossed the
promotion threshold in matched end-to-end testing. Those candidates were not
made production defaults.

### VAE timing

An opt-in VAE profile measured video and audio decode separately on a 124-frame
native run. Video decode was measurable, but combined VAE work was only about
6.3% of the total execution time at the tested resolution. This made VAE decode
a secondary target rather than the first optimization lever.

### AdaLN timing

The first-block AdaLN projection was approximately 0.33 ms in the measured
profiles. Its estimated aggregate contribution was a small fraction of total
render time, so an AdaLN cache was not implemented or promoted.

### Backend decision

The reference control remains the native INT8/ConvRot path with the normal
PyTorch attention route. More backend switching, generic attention toggles,
CPU encoder placement, and profiler-only improvements were deprioritized because
they did not improve matched finished-clip time.

## 3. Work-reduction accelerators

The useful direction was to reduce the number of full H3 transformer evaluations
while preserving native output heads, reconstruction, and normal ComfyUI graph
contracts as much as possible.

### Spectrum

Spectrum captures actual hidden features on selected solver steps, forecasts
future features using a small feature forecaster, and uses an offline replay path
for the standard audio-safe configuration. The node preserves native transformer
calls at anchors and labels forecast/fallback behavior for debugging.

Important limitations:

- Forecasting changes the denoising trajectory.
- It is not lossless or bit-identical to Native.
- Quality can vary by prompt, seed, sampler, checkpoint, resolution, and branch
  topology.
- The standard public defaults keep direct audio blending disabled and use the
  replay path that addressed the reproduced audio-degradation case.
- Broader prompt and seed coverage is still required.

### FirstBlockCache Safe

FirstBlockCache Safe reuses first-block work under conservative temporal guards.
The tested safe configuration limited consecutive cache hits and retained a
native control path. It produced a useful speedup in the matched comparison,
but the long-form campaign showed that audio level and quality still require
careful validation for each workflow.

### Turbo

Turbo applies the tested H3 Turbo LoRA and dedicated sampler path. It reduces the
number of solver steps and therefore gives a larger speedup than cache-only
methods. Turbo 8 is the useful fast lane from the long-form campaign. Turbo 6
was the fastest short-run draft, but it showed the largest trajectory and visual
regressions and is not presented as a quality candidate.

The Turbo weight is intentionally not redistributed. Users must obtain any
required model or LoRA files from an authorized source.

## 4. Measured results

### Short matched campaign

All values below are measured warm end-to-end execution times for 39 frames,
1.625 seconds, 608x352, and 20 steps unless noted.

| Lane | Time | Speedup vs Native | Interpretation |
|---|---:|---:|---|
| Native 20 | 87.129 s | 1.000x | Quality/reference control |
| Spectrum 20 | 59.951 s | 1.453x | Closest sampled behavior to Native |
| FBC Safe 20 | 56.327 s | 1.547x | Conservative acceleration candidate |
| Turbo 8 | 42.998 s | 2.026x | Fast measured lane |
| Turbo 6 | 34.439 s | 2.530x | Draft-only short-run lane |

### Long-form campaign

The long-form gate used 124 frames, approximately 5.167 seconds, 608x352, 24
fps, 20 steps, and one matched prompt/seed.

| Lane | Time | Speedup vs Native | Evidence status |
|---|---:|---:|---|
| Native 20 | 444.671 s / 7.4 min | 1.000x | Control |
| Spectrum 20 | 279.322 s / 4.7 min | 1.592x | Quality candidate, provisional |
| FBC Safe 20 | 301.975 s / 5.0 min | 1.473x | Conservative candidate, provisional |
| Turbo 8 | 208.391 s / 3.5 min | 2.134x | Fast lane, provisional quality |

The long-form outputs passed structural validation for H.264 video, AAC audio,
124 decoded frames, 24 fps, 32 kHz stereo, matching approximately 5.167-second
video/audio duration, and full decode without reported ffmpeg errors. Structural
validation is not the same as perceptual quality validation.

## 5. Quality and safety of interpretation

The experiments used matched prompts and seeds, but a single prompt and seed do
not establish general quality. Human review found broadly coherent long-form
structure for the Native, Spectrum, and FBC Safe samples. Turbo 8 remained
coherent but followed a visibly different facial, lighting, and motion trajectory.

The following were not fully machine-scored in the reference campaign:

- syllable-level speech synchronization;
- automated transcript accuracy;
- transient audio-to-motion event timing;
- every-frame perceptual review;
- broad identity or reference consistency across seeds;
- generalization to all H3 samplers and conditioning modes.

Therefore the project uses these labels:

- Native: control/reference lane.
- Spectrum: closest-to-native candidate, not guaranteed equivalent.
- FBC Safe: conservative acceleration candidate, still workflow-dependent.
- Turbo 8: fast lane with provisional quality.
- Turbo 6: draft-only exploratory lane.

## 6. What was not promoted

The following paths were deliberately not made public defaults:

- AOTriton environment changes.
- Generic alternative attention backends.
- CPU encoder placement for speed.
- Profiler-only synchronization timings.
- Unmatched synthetic GEMM results.
- AdaLN precomputation.
- VAE changes based only on the low-resolution timing split.
- Aggressive cache settings without matched quality review.
- Stacking multiple accelerators in one workflow.
- Unverified kernel changes that did not improve finished-clip timing.

This is intentional. A benchmark result is not a promotion decision until the
whole output is valid and the quality trade-off is documented.

## 7. Reproducible evaluation method

For a new machine or workflow:

1. Install native H3 and produce a short control clip.
2. Record ComfyUI, PyTorch, ROCm, GPU class, model revision, resolution, FPS,
   frame count, sampler, steps, seed, and prompt class.
3. Warm the server before timing the control.
4. Run one accelerator at a time with identical settings.
5. Record wall-clock execution and ComfyUI execution separately when possible.
6. Validate the final media with ffprobe/ffmpeg.
7. Review video and audio separately.
8. Repeat difficult cases with multiple seeds.
9. Restore or re-run Native after experiments.
10. Sanitize the result before sharing publicly.

The public benchmark tool defaults to localhost and accepts `COMFYUI_SERVER` or
an explicit `--server` value. It does not contain a private machine address.

## 8. Public package design

The repository is a meta-package rather than a fork of all ComfyUI. It includes:

- reusable custom-node components;
- a standalone benchmark graph runner;
- an installer that links components into a user-selected ComfyUI checkout;
- workflows without model files;
- tests, guides, and a sanitized reference-result example;
- an automated public-content policy check.

Each third-party component retains its original license. The new integration
glue and documentation use the repository's Apache-2.0 license. See `NOTICE.md`.

## 9. Known limitations and next work

- Test on a second AMD system before making performance claims broader.
- Repeat the long-form matrix across prompts and seeds.
- Add automated audio transcription and event timing where practical.
- Separate startup, model-load, queue, denoise, decode, and encode time in the
  benchmark report.
- Test longer real campaigns instead of relying only on linear projections.
- Keep the native lane as a permanent regression control.
- Revisit exact kernel work only if a candidate improves matched end-to-end clips.
- Revisit higher-resolution VAE and attention work only in the resolution regime
  where those costs dominate.

## Conclusion

The defensible public result is not that every H3 video becomes fast or that an
accelerator is universally safe. The defensible result is narrower and useful:

- Native H3 works locally on AMD ROCm in the tested configuration.
- The major low-resolution cost is repeated H3 transformer work.
- Several opt-in work-reduction lanes produce real measured speedups.
- Spectrum and FBC Safe are quality-oriented candidates.
- Turbo 8 is the measured fast lane.
- Turbo 6 remains exploratory.
- The public package preserves controls, labels uncertainty, excludes model
  weights and private data, and gives other users a reproducible starting point.
