# Notices, attribution, and modification record

This repository is a mixed-license source integration bundle. It does not
redistribute MiniMax H3, Qwen, VAE, or Turbo model weights. Users must obtain
model files separately and follow each model's license and usage terms.

## Vendored components

- `custom_nodes/ComfyUI-MiniMax-H3-Turbo/`
  - Upstream: https://github.com/Larryvrh/ComfyUI-MiniMax-H3-Turbo
  - Commit: `55fee864dd7b2976b1c4ce3c3d5f7968f181409f`
  - License: Apache-2.0, retained in the component directory.
  - The upstream packaging archive `node.zip` is omitted.
  - The bundled example workflow is updated to the promoted eight-step v4
    step-600 model selections; sampler help text now documents the supported
    four-to-eight-step range.
  - The required pruned-checkpoint interpolation grid is retained and verified.
- `custom_nodes/ComfyUI-MiniMaxH3-FirstBlockCache/`
  - Upstream: https://github.com/duckyshell/ComfyUI-MiniMaxH3-FirstBlockCache
  - Commit: `725973c3bfd9de6dce249bc93dc5fe27f820df31`
  - License: MIT, retained in the component directory.
  - Modified locally to disable cross-call reuse without stable UUID metadata,
    add regression coverage, remove a hard-coded local output path, and replace
    omitted generated benchmark evidence with immutable upstream references.
- `custom_nodes/ComfyUI-Spectrum-MiniMax-H3/`
  - Upstream: https://github.com/xmarre/ComfyUI-Spectrum-MiniMax-H3
  - Commit: `4b9a7d1163348c67e7e475423f24f8b7abb23565`
  - Version: 0.2.5.
  - License: GPL-3.0-or-later, retained in the component directory.
  - No local source changes.

Machine-readable tree hashes, runtime-asset checksums, versions, and local-change
records are in `vendored-components.json`.

## Workflow sources

- `workflows/h3-native-t2v.json` is byte-identical to Comfy Org's MiniMax H3
  template at workflow-templates commit
  `5c75d9f137bb27706a70dd337dac6249b2e51ded`. It remains MIT-licensed;
  see `LICENSE-COMFY-WORKFLOW-TEMPLATES-MIT.txt`.
- `workflows/h3-turbo8-t2v.json` is a modified form of the Apache-2.0 Turbo
  example at the pinned Turbo commit above. The promoted Spectrum and FBC UI
  workflows are generated derivatives of that graph and retain that source
  boundary. Exact paths are recorded in `vendored-components.json`.
- API prompt graphs, generators, tests, documentation, and other original
  integration glue are licensed under Apache-2.0; see
  `LICENSE-APACHE-2.0.txt`.

## Original bundle material

`tools/`, root `tests/`, API prompt graphs, root documentation, and other
original integration glue are licensed under Apache-2.0. This license does not
relicense vendored components or third-party workflow templates.

ComfyUI is a separate upstream project and is not vendored here:
https://github.com/Comfy-Org/ComfyUI

When redistributing a modified component, preserve its original license and
notices and clearly mark changed files as changed.
