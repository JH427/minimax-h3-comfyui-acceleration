#!/usr/bin/env python3
"""Matched MiniMax H3 accelerator tracer for public reproducibility.

This standalone graph runner never changes the production workflow. Accelerators
are mutually exclusive by construction.
"""
import argparse
import json
import os
import time
import urllib.parse
import urllib.request


def link(node, slot=0):
    return [str(node), slot]


def default_steps(accel: str) -> int:
    return 8 if accel == "turbo" else 20


def valid_frame_count(length: int) -> bool:
    return length >= 5 and (length - 5) % 17 == 0


def validate_http_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("ComfyUI endpoint must use HTTP or HTTPS")
    if not parsed.hostname:
        raise ValueError("ComfyUI endpoint must include a hostname")
    return url


def post_json(url, payload, timeout=30):
    validate_http_url(url)
    body = json.dumps(payload).encode()
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310
        return json.loads(response.read().decode())


def get_json(url, timeout=30):
    validate_http_url(url)
    with urllib.request.urlopen(url, timeout=timeout) as response:  # nosec B310
        return json.loads(response.read().decode())


def prompt_graph(args):
    graph = {
        "6": {"class_type": "UNETLoader", "inputs": {
            "unet_name": args.model,
            "weight_dtype": "default",
        }},
        "13": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": args.encoder,
            "type": "minimax",
            "device": args.encoder_device,
        }},
        "11": {"class_type": "VAELoader", "inputs": {
            "vae_name": "minimax_h3_video_vae_fp16.safetensors",
        }},
        "24": {"class_type": "VAELoader", "inputs": {
            "vae_name": "minimax_h3_audio_vae_fp32.safetensors",
        }},
        "104": {"class_type": "MiniMaxH3ImageToVideo", "inputs": {
            "clip": link(13),
            "vae": link(11),
            "prompt": args.prompt,
            "width": args.width,
            "height": args.height,
            "length": args.length,
        }},
        "15": {"class_type": "RandomNoise", "inputs": {"noise_seed": args.seed}},
        "16": {"class_type": "BasicGuider", "inputs": {
            "model": link(6),
            "conditioning": link(104),
        }},
        "17": {"class_type": "KSamplerSelect", "inputs": {
            "sampler_name": "res_multistep",
        }},
        "9": {"class_type": "BasicScheduler", "inputs": {
            "model": link(6),
            "scheduler": "simple",
            "steps": args.steps,
            "denoise": 1.0,
        }},
        "14": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": link(15),
            "guider": link(16),
            "sampler": link(17),
            "sigmas": link(9),
            "latent_image": link(104, 1),
        }},
        "10": {"class_type": "VAEDecode", "inputs": {
            "samples": link(14), "vae": link(11),
        }},
        "23": {"class_type": "VAEDecodeAudio", "inputs": {
            "samples": link(14), "vae": link(24),
        }},
        "91": {"class_type": "CreateVideo", "inputs": {
            "images": link(10),
            "fps": 24.0,
            "audio": link(23),
            "bit_depth": 8,
        }},
        "92": {"class_type": "SaveVideo", "inputs": {
            "video": link(91),
            "filename_prefix": f"video/{args.prefix}",
            "format": "auto",
            "codec": "auto",
        }},
    }

    model_link = link(6)
    if args.accel == "fbc-safe":
        graph["200"] = {"class_type": "ApplyMiniMaxH3FirstBlockCache", "inputs": {
            "model": link(6),
            "mode": "H3 Safe — 0.08 / max 2",
            "threshold": 0.08,
            "start_percent": 0.10,
            "end_percent": 0.95,
            "max_consecutive_hits": 2,
            "temporal_guard": False,
        }}
        model_link = link(200)
    elif args.accel == "turbo":
        graph["201"] = {"class_type": "MiniMaxH3TurboLoRA", "inputs": {
            "model": link(6),
            "lora_name": args.turbo_lora,
            "strength": 1.0,
            "low_vram": False,
        }}
        graph["202"] = {"class_type": "MiniMaxH3TurboSampler", "inputs": {}}
        model_link = link(201)
        graph["14"]["inputs"]["sampler"] = link(202)
    elif args.accel == "spectrum":
        graph["203"] = {"class_type": "SpectrumApplyMiniMaxH3", "inputs": {
            "model": link(6),
            "enabled": True,
            "blend_weight": 0.50,
            "degree": 1,
            "ridge_lambda": 0.10,
            "window_size": 2.0,
            "flex_window": 0.75,
            "warmup_steps": 1,
            "tail_actual_steps": 1,
            "max_history": 8,
            "debug": True,
            "history_storage": "system_ram",
            "bootstrap_first_forecast": True,
            "anchor_residual_feedback": False,
            "selective_rollback_correction": False,
            "offline_smoothing_replay": True,
            "audio_blend_weight": 0.0,
            "offline_archive_storage": "system_ram",
        }}
        model_link = link(203)

    graph["16"]["inputs"]["model"] = model_link
    graph["9"]["inputs"]["model"] = model_link
    return graph


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--server",
        default=os.environ.get("COMFYUI_SERVER", "http://127.0.0.1:8188"),
        help="ComfyUI HTTP endpoint (default: COMFYUI_SERVER or localhost:8188)",
    )
    parser.add_argument("--model", default="minimax_h3_fl2va_pruned_int8_convrot.safetensors")
    parser.add_argument("--encoder", default="qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors")
    parser.add_argument("--encoder-device", default="default", choices=["default", "cpu"])
    parser.add_argument("--width", type=int, default=608)
    parser.add_argument("--height", type=int, default=352)
    parser.add_argument("--length", type=int, default=39)
    parser.add_argument(
        "--steps",
        type=int,
        default=None,
        help="Sampling steps (default: 8 for Turbo, 20 for other lanes)",
    )
    parser.add_argument("--seed", type=int, default=9001)
    parser.add_argument(
        "--accel",
        choices=["control", "fbc-safe", "turbo", "spectrum"],
        default="control",
    )
    parser.add_argument("--turbo-lora", default="minimax_h3_turbo_v4_step600_ema.safetensors")
    parser.add_argument("--prefix", default="MiniMax_H3_39f_accel")
    parser.add_argument("--label", default="unlabeled")
    parser.add_argument("--client-id", default="minimax-h3-acceleration-benchmark")
    parser.add_argument("--prompt", default=(
        "Single continuous shot, a red glass marble rolls slowly across a black reflective table, "
        "a narrow warm spotlight travels across its surface, tiny room tone and a soft "
        "glass tap at the end, photorealistic cinematic macro film, no text, no cuts."
    ))
    args = parser.parse_args()
    if args.steps is None:
        args.steps = default_steps(args.accel)
    if args.steps < 1:
        parser.error("--steps must be at least 1")
    if not valid_frame_count(args.length):
        parser.error("--length must follow the MiniMax H3 17*k+5 frame grid")
    base = validate_http_url(args.server).rstrip("/")
    submitted = time.time()
    prompt_id = post_json(base + "/prompt", {
        "prompt": prompt_graph(args),
        "client_id": args.client_id,
    })["prompt_id"]
    print(json.dumps({
        "event": "submitted", "prompt_id": prompt_id,
        "label": args.label, "accel": args.accel,
    }), flush=True)

    deadline = time.monotonic() + 3600
    while time.monotonic() < deadline:
        history = get_json(base + "/history/" + prompt_id)
        if prompt_id in history:
            item = history[prompt_id]
            messages = item.get("status", {}).get("messages", [])
            starts = [m[1]["timestamp"] for m in messages if m[0] == "execution_start"]
            ends = [m[1]["timestamp"] for m in messages if m[0] == "execution_success"]
            result = {
                "event": "completed",
                "prompt_id": prompt_id,
                "label": args.label,
                "accel": args.accel,
                "status": item.get("status", {}).get("status_str"),
                "execution_ms": (ends[-1] - starts[-1]) if starts and ends else None,
                "submit_to_result_ms": round((time.time() - submitted) * 1000),
                "outputs": item.get("outputs", {}),
                "messages": messages,
                "config": vars(args),
            }
            print(json.dumps(result, default=str), flush=True)
            return 0 if result["status"] == "success" else 2
        time.sleep(1)
    print(json.dumps({"event": "timeout", "prompt_id": prompt_id, "label": args.label}), flush=True)
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
