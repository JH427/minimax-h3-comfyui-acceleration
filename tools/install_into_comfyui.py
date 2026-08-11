#!/usr/bin/env python3
"""Install the bundled custom-node components into a ComfyUI checkout."""
import argparse
from pathlib import Path

COMPONENTS = (
    "ComfyUI-MiniMax-H3-Turbo",
    "ComfyUI-MiniMaxH3-FirstBlockCache",
    "ComfyUI-Spectrum-MiniMax-H3",
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--comfyui", type=Path, required=True, help="Path to a ComfyUI checkout")
    parser.add_argument("--copy", action="store_true", help="Copy instead of creating symlinks")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    target = args.comfyui.expanduser().resolve() / "custom_nodes"
    if not (args.comfyui / "main.py").exists():
        raise SystemExit(f"Not a ComfyUI checkout: {args.comfyui}")
    target.mkdir(parents=True, exist_ok=True)
    for name in COMPONENTS:
        source = repo / "custom_nodes" / name
        destination = target / name
        if destination.exists() or destination.is_symlink():
            print(f"skip existing: {destination}")
            continue
        if args.copy:
            import shutil
            shutil.copytree(source, destination)
        else:
            destination.symlink_to(source, target_is_directory=True)
        print(f"installed: {name}")


if __name__ == "__main__":
    main()
