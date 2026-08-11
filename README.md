# MiniMax H3 ComfyUI Acceleration Pack

Opt-in ComfyUI acceleration nodes, workflows, and benchmark tooling for MiniMax
H3 video generation, with an AMD ROCm reference campaign.

The native ComfyUI lane remains intact. An accelerator is active only when its
node is explicitly inserted into a workflow.

## Included lanes

- **Native 20** — unmodified control lane.
- **Spectrum 20** — feature forecasting with audio-safe offline replay defaults.
- **FBC Safe 20** — calibrated Safe preset, threshold 0.08, maximum two
  consecutive cache hits; the preset does **not** enable the optional temporal
  guard.
- **Turbo 8** — promoted v4 step-600 LoRA with the dedicated Turbo sampler.

Every lane has both a frontend-loadable UI workflow and a generated API prompt
graph. See `workflows/README.md` for the exact matrix.

## Reference measurements

These are measured warm end-to-end values from one AMD Strix Halo / Radeon 8060S
system. They are reference evidence, not guarantees for other hardware.

| Lane | 124 frames / 5.167 seconds | Speedup |
|---|---:|---:|
| Native 20 | 444.671 s | 1.000x |
| Spectrum 20 | 279.322 s | 1.592x |
| FBC Safe 20 | 301.975 s | 1.473x |
| Turbo 8 | 208.391 s | 2.134x |

Turbo 6 remains a draft experiment and is not promoted because its quality is
provisional. FBC measurements above use the named Safe preset without the
Custom-mode temporal guard.

## Requirements

- ComfyUI 0.31.0 or later. Spectrum requires APIs introduced after v0.30.0,
  beginning with commit `e377e263049f9338b4d12a3dd417b36ae62948ff`. Native MiniMax H3 support
  landed in [ComfyUI PR #15224](https://github.com/Comfy-Org/ComfyUI/pull/15224).
- Python 3.10+ in the ComfyUI environment.
- A compatible PyTorch GPU runtime. The published measurements used AMD ROCm;
  the bundled nodes also retain their upstream platform behavior.
- MiniMax H3 model files obtained separately under their own licenses.

Use the authoritative
[ComfyUI MiniMax H3 tutorial](https://docs.comfy.org/tutorials/video/minimax/minimax-h3)
for native model setup. See `docs/models.md` for exact directories and the model
licensing boundary.

This repository is a source integration bundle, not a pip-installable wheel.

## Install into ComfyUI

```bash
git clone https://github.com/JH427/minimax-h3-comfyui-acceleration.git
cd minimax-h3-comfyui-acceleration
python tools/install_into_comfyui.py --comfyui ~/ComfyUI
```

The installer preflights and verifies all three components, including the Turbo
pruned-checkpoint runtime grid. It creates symlinks by default. Use `--copy` when
symlinks are unsuitable.

Existing destinations cause a safe failure rather than being silently skipped.
Inspect them first, then use `--force` only when you intend to replace all three
bundle-managed destinations:

```bash
python tools/install_into_comfyui.py --comfyui ~/ComfyUI --force
```

Restart ComfyUI after installation. Full instructions: `docs/installation.md`.

## Workflow examples

Frontend UI workflows:

- `workflows/h3-native-t2v.json`
- `workflows/h3-spectrum-t2v.json`
- `workflows/h3-fbc-safe-t2v.json`
- `workflows/h3-turbo8-t2v.json`

Generated API graphs:

- `workflows/api/h3-native-20.json`
- `workflows/api/h3-spectrum-20.json`
- `workflows/api/h3-fbc-safe-20.json`
- `workflows/api/h3-turbo-8.json`

The API files are inner prompt graphs, not complete `/prompt` request bodies.
`workflows/README.md` provides the required envelope and an exact submission
example.

## Run the benchmark runner

Start ComfyUI locally, then run:

```bash
python tools/benchmark.py \
  --server http://127.0.0.1:8188 \
  --accel control \
  --length 124 \
  --label native-20
```

Other lanes:

```bash
python tools/benchmark.py --accel spectrum --length 124 --label spectrum-20
python tools/benchmark.py --accel fbc-safe --length 124 --label fbc-safe-20
python tools/benchmark.py --accel turbo --length 124 --label turbo-8
```

The runner defaults to 20 steps for Native, Spectrum, and FBC, and 8 steps for
Turbo. Explicit `--steps` values override those defaults. Frame counts must
follow H3's `17*k+5` grid. `COMFYUI_SERVER` can supply the endpoint; localhost is
the public default.

## Evidence policy

Separate:

- measured end-to-end results;
- structural validation;
- throughput projections;
- external/vendor/community claims;
- qualitative observations;
- unresolved limitations.

Keep prompt, seed, resolution, frame rate, steps, checkpoint, and warm state fixed
when comparing lanes. Validate produced media with `ffprobe` or `ffmpeg` before
reporting success. See `docs/benchmarking.md` and
`docs/public-engineering-report.md`.

## Tests and release checks

Dependency-light checks:

```bash
uv run --with pytest --no-project pytest -q
python tools/generate_api_examples.py --check
python tools/generate_ui_examples.py --check
python tools/check_public_content.py
python -m compileall -q tools tests custom_nodes
```

The vendored Spectrum tests run in root CI with CPU PyTorch. FirstBlockCache tests
require a compatible ComfyUI/PyTorch environment; CI also checks their source and
release contracts. Runtime rendering remains a separate hardware-backed gate.

## Licensing and provenance

This is a mixed-license source aggregation:

- Original integration glue, tests, API graphs, generators, and documentation:
  Apache-2.0.
- Native frontend workflow: Comfy Org MIT template, with its notice retained.
- Turbo, Spectrum, and FBC frontend workflows: derived from the Apache-2.0
  Turbo example.
- Turbo component: Apache-2.0.
- FirstBlockCache component: MIT, with local changes documented.
- Spectrum component: GPL-3.0-or-later.

Read `NOTICE.md`, `vendored-components.json`, and each component's license before
redistribution. The required Turbo `h3_silu_temb_grid.safetensors` is an audited
5.5 MB runtime interpolation table, not a model or LoRA weight; its immutable
source and checksum are recorded in `vendored-components.json`.

Model weights, LoRAs, generated media, private prompts, local logs, credentials,
and personal identifiers are excluded from the intended public package.

## Documentation

- `docs/installation.md`
- `docs/models.md`
- `docs/benchmarking.md`
- `docs/public-engineering-report.md`
- `docs/rocm.md`
- `docs/privacy.md`
- `SECURITY.md`
