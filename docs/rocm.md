# AMD ROCm notes

This pack is designed for ComfyUI installations where PyTorch can execute the
native MiniMax H3 path on the AMD GPU. It does not install or replace ROCm.

## Verify before debugging the nodes

```bash
rocminfo | grep -E 'Name:.*gfx|Marketing Name' | head
python - <<'PY'
import torch
print('torch:', torch.__version__)
print('cuda available:', torch.cuda.is_available())
if torch.cuda.is_available():
    print('device:', torch.cuda.get_device_name(0))
PY
```

If native H3 does not work, fix the base ComfyUI/ROCm installation first.

## Image-conditioning workaround

Some ROCm/MIOpen combinations have failed on the Qwen-VL 3D patch convolution.
This public pack does not silently replace ComfyUI core files. If your setup
shows that failure, isolate the compatibility patch in a separate, reviewed
branch or use the upstream fix when available.

## Safety rules

- Keep Native as a control.
- Do not enable multiple accelerator lanes at once.
- Do not compare profiler-instrumented timings with normal production timings.
- Record the exact ROCm/PyTorch/ComfyUI versions in private or sanitized reports.
- Never include host paths or LAN addresses in shared logs.
