#!/usr/bin/env python3
"""Fail if tracked public files contain blocked adult-content or private markers."""
import re
import subprocess
from pathlib import Path

# Build sensitive terms from fragments so this checker does not trigger on itself.
BLOCKED = tuple("".join(parts) for parts in (
    ("n", "sfw"), ("n", "udity"), ("n", "ude"),
    ("p", "ornographic"), ("p", "orn"), ("e", "rotic"),
    ("s", "exual"), ("f", "etish"), ("h", "entai"),
))
PRIVATE_MARKERS = (
    "/" + "home/",
    "/" + "Users/",
    "100." + "117." + "97." + "55",
    "joshua" + "@",
    "agent" + "mail",
)
PRIVATE_RE = re.compile(r"(?:" + "|".join(re.escape(x) for x in PRIVATE_MARKERS) + r")", re.I)


def main() -> int:
    files = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
    problems = []
    for name in files:
        if name == "docs/privacy.md" or name == "tools/check_public_content.py":
            continue
        path = Path(name)
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lowered = text.casefold()
        for term in BLOCKED:
            if re.search(r"\b" + re.escape(term) + r"\b", lowered):
                problems.append(f"blocked content term {term!r}: {name}")
        if PRIVATE_RE.search(text):
            problems.append(f"private marker: {name}")
        if path.suffix.casefold() in {".safetensors", ".ckpt", ".pt", ".pth", ".mp4", ".log", ".jsonl"}:
            problems.append(f"forbidden artifact: {name}")
    if problems:
        print("\n".join(problems))
        return 1
    print(f"public-content check passed: {len(files)} tracked files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
