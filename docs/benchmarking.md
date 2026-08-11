# Benchmarking guide

## Controlled comparison

Use one prompt and seed across all lanes. Keep these fixed:

- checkpoint and quantization;
- width and height;
- frame count and FPS;
- sampler and scheduler;
- step count;
- text encoder placement;
- cache state and warmup policy;
- output encoding settings.

Run Native first as the control. Run each accelerator separately. Restore or
reconfirm the native control after experiments.

## Example matrix

```bash
for lane in control fbc-safe spectrum; do
  python tools/benchmark.py \
    --server http://127.0.0.1:8188 \
    --accel "$lane" \
    --length 124 \
    --steps 20 \
    --seed 20260811 \
    --label "$lane-20"
done

python tools/benchmark.py \
  --server http://127.0.0.1:8188 \
  --accel turbo \
  --length 124 \
  --steps 8 \
  --seed 20260811 \
  --label turbo-8
```

## Recording results

Save a sanitized summary with:

- lane;
- measured execution time;
- frame count and duration;
- speedup versus the warm native control;
- output codec and decode result;
- quality review notes;
- software/hardware class;
- limitations.

Remove prompt IDs, local paths, hostnames, private IP addresses, usernames, and
raw logs before sharing.

## Projections

If projecting a different clip length, label it as a projection. A simple
throughput projection is:

```text
projected_seconds = measured_seconds * target_frames / measured_frames
```

This ignores startup, model-load, queue, memory-pressure, and encoding effects.
Use a real longer campaign before making production guarantees.
