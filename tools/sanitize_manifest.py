#!/usr/bin/env python3
"""Remove local identifiers from a benchmark JSON manifest.

This is deliberately conservative: it drops paths, IDs, host fields, and raw
message/log fields instead of trying to redact them in place.
"""
import argparse
import json
from pathlib import Path

DROP_KEYS = {
    "prompt_id", "client_id", "server", "host", "hostname", "machine_id",
    "file", "path", "output", "outputs", "messages", "logs", "local_path",
}

def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k not in DROP_KEYS}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.write_text(json.dumps(clean(data), indent=2, sort_keys=True) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
