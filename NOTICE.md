# Notices and attribution

This repository is an integration bundle. It does not redistribute MiniMax H3,
Qwen, VAE, or Turbo model weights. Users must obtain model files from their
respective official or permitted sources and follow each model's license.

## Included components

- `custom_nodes/ComfyUI-MiniMax-H3-Turbo/` — retained under its included Apache-2.0 license.
- `custom_nodes/ComfyUI-MiniMaxH3-FirstBlockCache/` — retained under its included MIT license.
- `custom_nodes/ComfyUI-Spectrum-MiniMax-H3/` — retained under its included GPL-3.0 license.
- `tools/benchmark.py`, tests, documentation, and integration glue authored for
  this bundle — Apache-2.0; see `LICENSE-APACHE-2.0.txt`.

ComfyUI is a separate upstream project and is not vendored here. See:
https://github.com/comfyanonymous/ComfyUI

When redistributing a modified component, preserve its original license and
attribution notices and clearly mark modified files as changed.
