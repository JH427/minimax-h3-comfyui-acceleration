# Model files and licensing boundary

Model files are intentionally excluded from this repository.

The benchmark graph expects filenames matching the user's local model registry,
including names similar to:

- `minimax_h3_fl2va_pruned_int8_convrot.safetensors`
- `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`
- `minimax_h3_video_vae_fp16.safetensors`
- `minimax_h3_audio_vae_fp32.safetensors`
- `minimax_h3_turbo_v4_step600_ema.safetensors`

These filenames are configuration defaults, not download instructions. Obtain
the corresponding files from authorized sources and verify their licenses,
model-card restrictions, and intended use before downloading.

Do not commit:

- `.safetensors`, `.ckpt`, `.pt`, `.pth`, `.bin` files;
- model caches;
- private reference images or videos;
- generated media containing identifiable people;
- private prompts or datasets.
