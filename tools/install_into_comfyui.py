#!/usr/bin/env python3
"""Install the bundled custom-node components into a ComfyUI checkout."""
import argparse
import shutil
import tempfile
from pathlib import Path

COMPONENTS = (
    "ComfyUI-MiniMax-H3-Turbo",
    "ComfyUI-MiniMaxH3-FirstBlockCache",
    "ComfyUI-Spectrum-MiniMax-H3",
)
REQUIRED_FILES = {
    "ComfyUI-MiniMax-H3-Turbo": ("__init__.py", "h3_silu_temb_grid.safetensors"),
    "ComfyUI-MiniMaxH3-FirstBlockCache": ("__init__.py", "nodes.py"),
    "ComfyUI-Spectrum-MiniMax-H3": ("__init__.py", "comfyui_spectrum_h3/nodes.py"),
}


def _remove_destination(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    else:
        shutil.rmtree(path)


def _verify_component(path: Path, name: str) -> None:
    missing = [relative for relative in REQUIRED_FILES[name] if not (path / relative).is_file()]
    if missing:
        raise RuntimeError(f"incomplete component {name}: missing {', '.join(missing)}")


def install_components(
    comfyui: Path,
    *,
    copy: bool = False,
    force: bool = False,
) -> list[Path]:
    """Install all components and return their verified destination paths."""
    comfyui = comfyui.expanduser().resolve()
    if not (comfyui / "main.py").is_file():
        raise ValueError(f"Not a ComfyUI checkout: {comfyui}")

    repo = Path(__file__).resolve().parents[1]
    target = comfyui / "custom_nodes"
    sources = {name: repo / "custom_nodes" / name for name in COMPONENTS}
    destinations = {name: target / name for name in COMPONENTS}

    for name, source in sources.items():
        _verify_component(source, name)
    if not force:
        existing = [path for path in destinations.values() if path.exists() or path.is_symlink()]
        if existing:
            raise FileExistsError(
                "destination already exists; inspect it or rerun with --force: "
                + ", ".join(str(path) for path in existing)
            )

    target.mkdir(parents=True, exist_ok=True)
    transaction = Path(tempfile.mkdtemp(prefix=".minimax-h3-install-", dir=target))
    staging = transaction / "staging"
    backups = transaction / "backups"
    staging.mkdir()
    backups.mkdir()
    promoted: list[str] = []
    try:
        for name in COMPONENTS:
            staged = staging / name
            if copy:
                shutil.copytree(sources[name], staged)
            else:
                staged.symlink_to(sources[name], target_is_directory=True)
            _verify_component(staged, name)

        for name in COMPONENTS:
            destination = destinations[name]
            backup = backups / name
            if destination.exists() or destination.is_symlink():
                destination.replace(backup)
            (staging / name).replace(destination)
            promoted.append(name)

        installed = [destinations[name] for name in COMPONENTS]
        for name, destination in destinations.items():
            _verify_component(destination, name)
        for name in COMPONENTS:
            print(f"installed and verified: {name}")
        return installed
    except Exception:
        for name in reversed(COMPONENTS):
            destination = destinations[name]
            backup = backups / name
            if backup.exists() or backup.is_symlink():
                if destination.exists() or destination.is_symlink():
                    _remove_destination(destination)
                backup.replace(destination)
            elif name in promoted and (destination.exists() or destination.is_symlink()):
                _remove_destination(destination)
        raise
    finally:
        shutil.rmtree(transaction, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--comfyui", type=Path, required=True, help="Path to a ComfyUI checkout")
    parser.add_argument("--copy", action="store_true", help="Copy instead of creating symlinks")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing component destinations after source preflight passes",
    )
    args = parser.parse_args()
    try:
        install_components(args.comfyui, copy=args.copy, force=args.force)
    except (FileExistsError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
