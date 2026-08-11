# Installation

## 1. Prepare native MiniMax H3

Use ComfyUI 0.31.0 or later. Native H3 support landed in
[ComfyUI PR #15224](https://github.com/Comfy-Org/ComfyUI/pull/15224), while the
bundled Spectrum lane requires APIs introduced after v0.30.0, beginning with
commit `e377e263049f9338b4d12a3dd417b36ae62948ff`.

Follow the authoritative
[MiniMax H3 tutorial](https://docs.comfy.org/tutorials/video/minimax/minimax-h3):

1. Update ComfyUI.
2. Open **Template Library → Video → MiniMax H3**.
3. Produce a native T2V control before installing an accelerator.

For a blank-machine installation, follow the official
[ComfyUI installation guide](https://docs.comfy.org/installation/overview) for
Python/environment setup and launch instructions. For a source checkout:

```bash
git clone https://github.com/Comfy-Org/ComfyUI.git
cd ComfyUI
git checkout v0.31.0  # or a newer stable release
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

This pack does not replace native H3 support.

## 2. Install this source bundle

```bash
git clone https://github.com/JH427/minimax-h3-comfyui-acceleration.git
cd minimax-h3-comfyui-acceleration
python tools/install_into_comfyui.py --comfyui ~/ComfyUI
```

The installer:

- expands and resolves `~` paths;
- preflights all component source files;
- verifies the required Turbo interpolation grid;
- installs all three components as symlinks by default;
- fails if any destination already exists.

Use `--copy` when symlinks are unsuitable:

```bash
python tools/install_into_comfyui.py --comfyui ~/ComfyUI --copy
```

To replace all existing bundle-managed destinations after inspecting them:

```bash
python tools/install_into_comfyui.py --comfyui ~/ComfyUI --force
```

`--force` is intentionally explicit. The installer stages and verifies all
three replacements, then swaps them into place while retaining backups for
rollback. A staging or promotion failure restores the original destinations.
Do not use it for custom-node directories containing uncommitted work you need
to preserve.

## 3. Install model files separately

Follow `docs/models.md`. Never place model files in this Git repository.

## 4. Restart and verify node loading

Restart ComfyUI and inspect its startup log. Confirm these classes are available:

- `MiniMaxH3TurboLoRA`
- `MiniMaxH3TurboSampler`
- `ApplyMiniMaxH3FirstBlockCache`
- `SpectrumApplyMiniMaxH3`

A quick API check is:

```bash
python - <<'PY'
import json, urllib.request
with urllib.request.urlopen('http://127.0.0.1:8188/object_info') as response:
    info = json.load(response)
required = {
    'MiniMaxH3TurboLoRA',
    'MiniMaxH3TurboSampler',
    'ApplyMiniMaxH3FirstBlockCache',
    'SpectrumApplyMiniMaxH3',
}
missing = sorted(required - info.keys())
if missing:
    raise SystemExit('missing nodes: ' + ', '.join(missing))
print('all acceleration nodes loaded')
PY
```

## 5. First smoke test

1. Load `workflows/h3-native-t2v.json` and run a short control.
2. Load exactly one accelerator workflow with the same prompt, seed, dimensions,
   and frame count.
3. Do not stack Spectrum, FirstBlockCache, and Turbo in a first comparison.
4. Confirm video and audio decode completely.

Use 39 frames for a short smoke test. H3 frame counts follow `17*k+5`. At
24 fps, 39 frames correspond to 1.625 seconds; enter `1.625` if a workflow
exposes duration rather than an explicit frame-count widget.

## Updating

The component directories installed by this bundle are not independent upstream
Git clones. Do not run `git pull` inside them.

Update the bundle itself, then reinstall:

```bash
cd minimax-h3-comfyui-acceleration
git pull --ff-only
python tools/install_into_comfyui.py --comfyui ~/ComfyUI --force
```

If you installed with `--copy`, `--force --copy` refreshes the copied components.
If you installed with symlinks, pulling the bundle updates their targets; rerun
the installer only when paths or verification requirements change.

Pinned upstream revisions and local changes are recorded in
`vendored-components.json`.
