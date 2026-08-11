#!/usr/bin/env python3
"""Generate frontend-loadable FBC and Spectrum workflows from the explicit H3 graph."""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "workflows" / "h3-turbo8-t2v.json"
OUTPUTS = {
    "h3-fbc-safe-t2v.json": "fbc-safe",
    "h3-spectrum-t2v.json": "spectrum",
}


def _node(workflow: dict, node_id: int) -> dict:
    return next(node for node in workflow["nodes"] if node["id"] == node_id)


def _model_patch_node(node_id: int, class_type: str, widgets: list, title: str) -> dict:
    return {
        "id": node_id,
        "type": class_type,
        "pos": [-1120.0, 4800.0],
        "size": [390, 360 if class_type.startswith("Spectrum") else 230],
        "flags": {},
        "order": 12,
        "mode": 0,
        "inputs": [{"name": "model", "type": "MODEL", "link": 249}],
        "outputs": [{"name": "MODEL", "type": "MODEL", "links": [250, 251]}],
        "title": title,
        "properties": {"Node name for S&R": class_type},
        "widgets_values": widgets,
    }


def _sampler_node(node_id: int) -> dict:
    return {
        "id": node_id,
        "type": "KSamplerSelect",
        "pos": [-826.0, 5412.0],
        "size": [280, 58],
        "flags": {},
        "order": 10,
        "mode": 0,
        "inputs": [],
        "outputs": [{"name": "SAMPLER", "type": "SAMPLER", "links": [252]}],
        "properties": {"Node name for S&R": "KSamplerSelect"},
        "widgets_values": ["res_multistep"],
    }


def build_workflow(lane: str) -> dict:
    workflow = json.loads(BASE.read_text(encoding="utf-8"))
    workflow = copy.deepcopy(workflow)
    scheduler = next(node for node in workflow["nodes"] if node["type"] == "BasicScheduler")
    scheduler["widgets_values"][1] = 20

    if lane == "fbc-safe":
        patch_node = _model_patch_node(
            134,
            "ApplyMiniMaxH3FirstBlockCache",
            ["H3 Safe — 0.08 / max 2", 0.08, 0.10, 0.95, 2, False],
            "FirstBlockCache — Safe preset (no temporal guard)",
        )
    elif lane == "spectrum":
        patch_node = _model_patch_node(
            134,
            "SpectrumApplyMiniMaxH3",
            [
                True,
                0.5,
                1,
                0.1,
                2.0,
                0.75,
                1,
                1,
                8,
                False,
                "system_ram",
                True,
                False,
                False,
                True,
                0.0,
                "system_ram",
            ],
            "Spectrum 20 — audio-safe offline replay",
        )
    else:
        raise ValueError(f"unknown lane: {lane}")

    workflow["nodes"] = [
        patch_node if node["id"] == 134 else _sampler_node(135) if node["id"] == 135 else node
        for node in workflow["nodes"]
    ]
    return workflow


def serialize(lane: str) -> str:
    return json.dumps(build_workflow(lane), indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = []
    for filename, lane in OUTPUTS.items():
        destination = ROOT / "workflows" / filename
        expected = serialize(lane)
        if args.check:
            if not destination.is_file() or destination.read_text(encoding="utf-8") != expected:
                stale.append(filename)
        else:
            destination.write_text(expected, encoding="utf-8")
            print(f"wrote workflows/{filename}")
    if stale:
        print("UI examples are stale: " + ", ".join(stale))
        return 1
    if args.check:
        print(f"UI examples match generator: {len(OUTPUTS)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
