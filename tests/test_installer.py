import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "tools"))
from install_into_comfyui import COMPONENTS, install_components  # noqa: E402


def fake_comfyui(root: Path) -> Path:
    comfyui = root / "ComfyUI"
    (comfyui / "custom_nodes").mkdir(parents=True)
    (comfyui / "main.py").write_text("", encoding="utf-8")
    return comfyui


def test_installer_expands_tilde_and_verifies_components(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    comfyui = fake_comfyui(tmp_path)

    installed = install_components(Path("~/ComfyUI"))

    assert {path.name for path in installed} == set(COMPONENTS)
    for path in installed:
        assert path.is_symlink()
    assert (
        comfyui
        / "custom_nodes"
        / "ComfyUI-MiniMax-H3-Turbo"
        / "h3_silu_temb_grid.safetensors"
    ).is_file()


def test_force_copy_failure_preserves_all_existing_components(tmp_path, monkeypatch):
    comfyui = fake_comfyui(tmp_path)
    destinations = []
    for name in COMPONENTS:
        destination = comfyui / "custom_nodes" / name
        destination.mkdir()
        (destination / "sentinel.txt").write_text(name, encoding="utf-8")
        destinations.append(destination)

    import install_into_comfyui as installer

    real_copytree = installer.shutil.copytree
    calls = 0

    def fail_second_copy(source, destination, *args, **kwargs):
        nonlocal calls
        if Path(source).parent.name == "custom_nodes":
            calls += 1
            if calls == 2:
                raise OSError("injected copy failure")
        return real_copytree(source, destination, *args, **kwargs)

    monkeypatch.setattr(installer.shutil, "copytree", fail_second_copy)

    with pytest.raises(OSError, match="injected copy failure"):
        install_components(comfyui, copy=True, force=True)

    for name, destination in zip(COMPONENTS, destinations, strict=True):
        assert (destination / "sentinel.txt").read_text(encoding="utf-8") == name
    assert not list((comfyui / "custom_nodes").glob(".minimax-h3-install-*"))


def test_installer_rejects_stale_destination_unless_force_is_explicit(tmp_path):
    comfyui = fake_comfyui(tmp_path)
    stale = comfyui / "custom_nodes" / COMPONENTS[0]
    stale.mkdir()
    (stale / "sentinel.txt").write_text("stale", encoding="utf-8")

    with pytest.raises(FileExistsError, match="destination already exists"):
        install_components(comfyui)

    installed = install_components(comfyui, force=True)
    assert len(installed) == len(COMPONENTS)
    assert stale.is_symlink()
