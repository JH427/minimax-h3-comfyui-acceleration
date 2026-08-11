# Workflow examples

## Frontend UI workflows

Load these files through the ComfyUI frontend:

| Lane | File | Steps | Sampler |
|---|---|---:|---|
| Native | `h3-native-t2v.json` | 20 | `res_multistep` |
| Spectrum | `h3-spectrum-t2v.json` | 20 | `res_multistep` |
| FBC Safe | `h3-fbc-safe-t2v.json` | 20 | `res_multistep` |
| Turbo | `h3-turbo8-t2v.json` | 8 | dedicated Turbo sampler |

Spectrum uses audio-safe offline replay defaults. FBC uses the named Safe preset;
its optional Custom-mode temporal guard is not enabled. Turbo uses the promoted
pruned INT8 base, NVFP4 encoder, and v4 step-600 LoRA filenames documented in
`docs/models.md`.

The Spectrum and FBC UI files are deterministically generated from the explicit
H3 graph. Verify them with:

```bash
python tools/generate_ui_examples.py --check
```

## API prompt graphs

The `api/` directory contains generated inner prompt graphs:

- `api/h3-native-20.json`
- `api/h3-spectrum-20.json`
- `api/h3-fbc-safe-20.json`
- `api/h3-turbo-8.json`

These files are not complete `/prompt` request bodies. ComfyUI expects the graph
under the `prompt` key, plus an optional `client_id`.

Exact submission example with `jq` and `curl`:

```bash
jq -n \
  --slurpfile graph workflows/api/h3-spectrum-20.json \
  '{prompt: $graph[0], client_id: "minimax-h3-public-example"}' \
| curl --fail-with-body \
    --header 'Content-Type: application/json' \
    --data-binary @- \
    http://127.0.0.1:8188/prompt
```

For submission, history polling, timing, and lane-correct step defaults, prefer:

```bash
python tools/benchmark.py --accel spectrum --length 39
```

Regenerate or verify API examples with:

```bash
python tools/generate_api_examples.py
python tools/generate_api_examples.py --check
```

All public examples use a benign synthetic marble prompt, 608x352, 39 frames,
and seed 9001. Model weights and generated media are not included.
