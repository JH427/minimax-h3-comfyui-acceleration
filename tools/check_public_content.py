#!/usr/bin/env python3
"""Fail when tracked public files contain private, unsafe, or excluded material."""
import ipaddress
import re

# Required only to invoke `git ls-files` with fixed argv and no shell.
import subprocess  # nosec B404
from pathlib import Path

# Build sensitive terms from fragments so this checker does not trigger on itself.
BLOCKED = tuple(
    "".join(parts)
    for parts in (
        ("n", "sfw"),
        ("n", "udity"),
        ("n", "ude"),
        ("p", "ornographic"),
        ("p", "orn"),
        ("e", "rotic"),
        ("s", "exual"),
        ("f", "etish"),
        ("h", "entai"),
    )
)
AUDITED_RUNTIME_ASSETS = {
    Path("custom_nodes/ComfyUI-MiniMax-H3-Turbo/h3_silu_temb_grid.safetensors")
}
FORBIDDEN_ARTIFACT_EXTENSIONS = {
    ".bin",
    ".ckpt",
    ".gif",
    ".gguf",
    ".jpeg",
    ".jpg",
    ".jsonl",
    ".log",
    ".m4a",
    ".mkv",
    ".mov",
    ".mp3",
    ".mp4",
    ".onnx",
    ".otf",
    ".png",
    ".pt",
    ".pth",
    ".safetensors",
    ".tiff",
    ".wav",
    ".webm",
    ".webp",
}
HOME_PATH_RE = re.compile(
    r"(?:/(?:home|Users)/[A-Za-z0-9._-]+|[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9._-]+)",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
IPV4_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
IPV6_RE = re.compile(
    r"(?<![0-9A-Fa-f:])(?:[0-9A-Fa-f]{0,4}:){2,7}[0-9A-Fa-f]{0,4}"
    r"(?![0-9A-Fa-f:])"
)
ASSIGNMENT_RE = re.compile(
    r"\b(?P<name>[A-Z][A-Z0-9_-]{1,100})\b\s*[:=]\s*['\"]?"
    r"(?P<value>[^'\"\s]{8,})['\"]?",
    re.IGNORECASE,
)
BEARER_RE = re.compile(r"\bauthorization\s*:\s*bearer\s+\S{8,}", re.IGNORECASE)
PRIVATE_KEY_MARKER = "-----BEGIN " + "PRIVATE KEY-----"


def _normalized_identifier(value: str) -> str:
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value.strip())
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _credential_name(value: str) -> bool:
    normalized = _normalized_identifier(value)
    exact = {"api_key", "auth", "authorization", "passwd", "password", "secret", "token"}
    suffixes = (
        "_api_key",
        "_secret_access_key",
        "_access_key",
        "_access_token",
        "_token",
        "_client_secret",
        "_secret",
        "_password",
        "_passwd",
        "_private_key",
    )
    return normalized in exact or normalized.endswith(suffixes)


def _has_credential_assignment(text: str) -> bool:
    return any(_credential_name(match.group("name")) for match in ASSIGNMENT_RE.finditer(text))


def _private_ips(text: str) -> list[str]:
    matches = []
    for candidate in IPV4_RE.findall(text) + IPV6_RE.findall(text):
        if candidate == "::":
            continue
        try:
            address = ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if address.is_loopback:
            continue
        if address.is_private or address.is_link_local or address.is_reserved:
            matches.append(candidate)
    return matches


def find_text_problems(path: Path, text: str) -> list[str]:
    """Return public-content violations found in one text file."""
    problems = []
    lowered = text.casefold()
    for term in BLOCKED:
        if re.search(r"\b" + re.escape(term) + r"\b", lowered):
            problems.append(f"blocked content term {term!r}: {path}")
    if HOME_PATH_RE.search(text):
        problems.append(f"private home path: {path}")
    if EMAIL_RE.search(text):
        problems.append(f"email address: {path}")
    if _private_ips(text):
        problems.append(f"private IP address: {path}")
    if _has_credential_assignment(text) or BEARER_RE.search(text):
        problems.append(f"credential-like assignment: {path}")
    if PRIVATE_KEY_MARKER in text:
        problems.append(f"private key material: {path}")
    return problems


def artifact_problem(path: Path) -> str | None:
    normalized = Path(path.as_posix())
    if normalized in AUDITED_RUNTIME_ASSETS:
        return None
    if path.suffix.casefold() in FORBIDDEN_ARTIFACT_EXTENSIONS:
        return f"forbidden artifact: {path}"
    return None


def public_files(root: Path = Path(".")) -> list[Path]:
    """List tracked files, or all source-archive files when Git metadata is absent."""
    # Fixed executable/arguments; root is passed as one argv element, never a shell.
    result = subprocess.run(  # nosec B603 B607
        ["git", "-C", str(root), "ls-files"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode == 0:
        return [Path(name) for name in result.stdout.splitlines()]

    ignored_parts = {".git", ".pytest_cache", ".ruff_cache", "__pycache__"}
    return sorted(
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and not ignored_parts.intersection(path.relative_to(root).parts)
    )


def main() -> int:
    files = public_files()
    problems = []
    for path in files:
        name = path.as_posix()
        artifact = artifact_problem(path)
        if artifact:
            problems.append(artifact)
        if path in AUDITED_RUNTIME_ASSETS or name == "tools/check_public_content.py":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        problems.extend(find_text_problems(path, text))
    if problems:
        print("\n".join(problems))
        return 1
    print(f"public-content check passed: {len(files)} tracked files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
