# Model files and licensing boundary

Model files are intentionally excluded from this repository. Obtain them from
sources you are authorized to use, review their model cards and licenses, and
verify file integrity before loading them.

The authoritative native setup is the
[ComfyUI MiniMax H3 tutorial](https://docs.comfy.org/tutorials/video/minimax/minimax-h3).
Native H3 files are hosted in the
[Comfy-Org/MiniMax-H3 model repository](https://huggingface.co/Comfy-Org/MiniMax-H3).

## Expected local layout

| Role | Default filename | Destination |
|---|---|---|
| Diffusion model | `minimax_h3_fl2va_pruned_int8_convrot.safetensors` | `ComfyUI/models/diffusion_models/` |
| Text encoder | `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | `ComfyUI/models/text_encoders/` |
| Video VAE | `minimax_h3_video_vae_fp16.safetensors` | `ComfyUI/models/vae/` |
| Audio VAE | `minimax_h3_audio_vae_fp32.safetensors` | `ComfyUI/models/vae/` |
| Turbo LoRA | `minimax_h3_turbo_v4_step600_ema.safetensors` | `ComfyUI/models/loras/` |

The Turbo LoRA source and usage guidance are maintained by the upstream
[MiniMax-H3 Turbo LoRA project](https://huggingface.co/larryvrh/MiniMax-H3-Turbo-Lora).

The frontend workflows contain official model-card or model-file links inherited
from ComfyUI templates. Those links are convenience references and may target a
mutable branch. Review the associated model card and prefer an immutable revision
or a locally recorded checksum for production use.

## Runtime support asset versus model weights

The bundle intentionally includes:

`custom_nodes/ComfyUI-MiniMax-H3-Turbo/h3_silu_temb_grid.safetensors`

Despite its extension, this is not a generative model, encoder, VAE, or LoRA. It
is a small interpolation table required by the upstream Turbo node when applying
AdaLN updates to pruned H3 checkpoints. Its exact upstream commit, size, role,
and SHA-256 are recorded in `vendored-components.json` and enforced by tests.

## Never commit

- Model, encoder, VAE, or LoRA weights.
- Model caches.
- Generated video, audio, or image evidence.
- Private reference media.
- Private prompts or datasets.
- Raw runtime logs or unsanitized manifests.

The audited Turbo runtime table above is the only tracked binary-data exception.
