# MiniMax H3 ComfyUI Acceleration Pack

Optional ComfyUI nodes and benchmark tooling for MiniMax H3 video generation on
AMD ROCm systems.

The project keeps the native ComfyUI lane intact. An accelerator is active only
when its node is explicitly inserted into a workflow.

## What is included

- Spectrum H3 feature forecasting.
- FirstBlockCache Safe H3 caching.
- Turbo H3 sampler/LoRA integration.
- A standalone HTTP benchmark runner.
- Contract tests for the generated ComfyUI graphs.
- Example workflows without model weights or generated media.
- Reproducible measurement and output-validation guides.

## Reference measurements

These are measurements from one AMD Strix Halo / Radeon 8060S system. They are
reference values, not guarantees for other hardware.

| Lane | 124 frames / 5.167 seconds | Speedup |
|---|---:|---:|
| Native 20 | 444.671 s | 1.000x |
| Spectrum 20 | 279.322 s | 1.592x |
| FBC Safe 20 | 301.975 s | 1.473x |
| Turbo 8 | 208.391 s | 2.134x |

Turbo 6 is retained as a draft experiment and is not included in the long-form
promotion table because its quality is provisional.

## Requirements

- ComfyUI with native MiniMax H3 support.
- Python 3.10+.
- PyTorch/ROCm compatible with the host GPU.
- MiniMax H3 model files obtained separately.
- The custom nodes' upstream compatibility requirements.

This repository does not contain model weights. See `docs/models.md` for the
expected filenames and licensing boundary.

## Install into ComfyUI

Clone the repository anywhere, then install the components into ComfyUI:

```bash
git clone https://github.com/JH427/minimax-h3-comfyui-acceleration.git
cd minimax-h3-comfyui-acceleration
python tools/install_into_comfyui.py --comfyui /path/to/ComfyUI
```

The installer creates symlinks from `ComfyUI/custom_nodes/` to the three bundled
component directories. Use `--copy` instead if symlinks are unsuitable.

- `docs/installation.md`
- `docs/benchmarking.md`
- `docs/rocm.md`
- `docs/models.md`

## Run the benchmark runner

Start ComfyUI locally, then run:

```bash
python tools/benchmark.py \
  --server http://127.0.0.1:8188 \
  --accel control \
  --length 124 \
  --steps 20 \
  --label native-20
```

Other lanes:

```bash
python tools/benchmark.py --accel spectrum --length 124 --label spectrum-20
python tools/benchmark.py --accel fbc-safe --length 124 --label fbc-safe-20
python tools/benchmark.py --accel turbo --length 124 --steps 8 --label turbo-8
```

The endpoint can also be supplied through `COMFYUI_SERVER`. The default is
localhost; no private LAN address is embedded in the code.

## Evidence policy

Benchmark results should distinguish:

- measured wall-clock results;
- projections derived from measured throughput;
- model/vendor claims;
- quality observations;
- unresolved limitations.

Use the same prompt, seed, resolution, frame rate, steps, checkpoint, and cache
state when comparing lanes. Validate the resulting MP4 with `ffprobe` or
`ffmpeg` before reporting success.

## Tests

The default test command covers the dependency-free graph-contract tests:

```bash
python -m pytest -q
```

The vendored component tests are retained under each component's `tests/`
directory. Run them inside a compatible ComfyUI/PyTorch environment; they are
not expected to run in a plain documentation-only checkout.

## Licensing

The original integration glue, benchmark runner, tests, and documentation are
Apache-2.0. Vendored components retain their own licenses. Read `NOTICE.md` and
the license file in each component directory before redistributing modified
versions.

No personal data, private hostnames, private IP addresses, email addresses,
mailbox identifiers, local absolute paths, model weights, generated media, or
raw local logs are part of the intended public package.
