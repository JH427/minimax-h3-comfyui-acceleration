# Installation

## 1. Prepare ComfyUI

Use a clean ComfyUI installation with native MiniMax H3 support. Do not copy
the entire Horizon-specific ComfyUI checkout over an existing installation.

```bash
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
```

Use the ComfyUI revision documented by the H3 model integration you install.
The acceleration components are not a replacement for native H3 support.

## 2. Install this pack

Clone the repository anywhere, then run the installer:

```bash
git clone https://github.com/JH427/minimax-h3-comfyui-acceleration.git
cd minimax-h3-comfyui-acceleration
python tools/install_into_comfyui.py --comfyui /path/to/ComfyUI
```

Use `--copy` instead of symlinks if required by your environment.

## 3. Install model files separately

Follow `docs/models.md`. Never place model files in this Git repository.

## 4. Verify node loading

Start ComfyUI and inspect its startup log. Confirm the node classes load without
errors before running a generation. A missing optional accelerator should fail
clearly; native H3 should remain usable.

## 5. First smoke test

Run a short native job first. Then run exactly the same job with one accelerator
added. Do not stack Spectrum, FirstBlockCache, and Turbo in a first comparison.
