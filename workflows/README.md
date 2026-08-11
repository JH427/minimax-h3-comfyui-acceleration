# Workflow examples

This directory contains two kinds of examples:

- `h3-native-t2v.json` and `h3-turbo8-t2v.json` are ComfyUI UI workflow files
  intended for loading in the frontend.
- `api/` contains API-format prompt graphs generated from
  `tools/benchmark.py`. Submit one to a compatible ComfyUI `/prompt` endpoint
  or use it as a reference when building a UI graph.

API lane examples:

- `api/h3-native-20.json` — native control, 20 steps.
- `api/h3-spectrum-20.json` — Spectrum with audio-safe replay defaults.
- `api/h3-fbc-safe-20.json` — conservative FirstBlockCache configuration.
- `api/h3-turbo-8.json` — Turbo 8 sampler lane.

The API examples use a benign synthetic marble prompt, 608x352, 39 frames, and
seed 9001. Change model filenames to match your local model registry. No model
weights or generated media are included.

For a complete HTTP runner with timing and history polling, use:

```bash
python tools/benchmark.py --accel spectrum --length 39 --steps 20
```
