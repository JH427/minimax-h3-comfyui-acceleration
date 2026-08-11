#!/usr/bin/env python3
"""Generate or verify the canonical public ComfyUI API prompt graphs."""
import argparse
import json
from argparse import Namespace
from pathlib import Path

from benchmark import prompt_graph

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "workflows" / "api"
PROMPT = (
    "Single continuous shot of a red glass marble rolling slowly across a black "
    "reflective table while a warm spotlight crosses the surface; one soft glass "
    "tap at the end; photorealistic macro film; no text; no cuts."
)
LANES = {
    "h3-native-20.json": ("control", 20),
    "h3-spectrum-20.json": ("spectrum", 20),
    "h3-fbc-safe-20.json": ("fbc-safe", 20),
    "h3-turbo-8.json": ("turbo", 8),
}


def lane_args(accel: str, steps: int) -> Namespace:
    return Namespace(
        model="minimax_h3_fl2va_pruned_int8_convrot.safetensors",
        encoder="qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors",
        encoder_device="default",
        width=608,
        height=352,
        length=39,
        steps=steps,
        seed=9001,
        prefix="MiniMax_H3_public_example",
        prompt=PROMPT,
        accel=accel,
        turbo_lora="minimax_h3_turbo_v4_step600_ema.safetensors",
        label="public-example",
        client_id="minimax-h3-public-example",
    )


def serialized_graph(accel: str, steps: int) -> str:
    return json.dumps(prompt_graph(lane_args(accel, steps)), indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if checked-in graphs differ")
    args = parser.parse_args()
    mismatches = []
    for filename, (accel, steps) in LANES.items():
        destination = OUTPUT_DIR / filename
        expected = serialized_graph(accel, steps)
        if args.check:
            if not destination.is_file() or destination.read_text(encoding="utf-8") != expected:
                mismatches.append(str(destination.relative_to(ROOT)))
        else:
            destination.write_text(expected, encoding="utf-8")
            print(f"wrote {destination.relative_to(ROOT)}")
    if mismatches:
        print("API examples are stale: " + ", ".join(mismatches))
        return 1
    if args.check:
        print(f"API examples match generator: {len(LANES)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
