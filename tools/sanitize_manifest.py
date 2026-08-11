#!/usr/bin/env python3
"""Remove sensitive identifiers and values from a benchmark JSON manifest."""
import argparse
import ipaddress
import json
import re
from pathlib import Path

REDACTED = "[REDACTED]"
DROP_KEYS = {
    "api_key",
    "auth",
    "authorization",
    "client_id",
    "email",
    "file",
    "host",
    "hostname",
    "local_path",
    "logs",
    "machine_id",
    "messages",
    "output",
    "outputs",
    "password",
    "path",
    "prompt",
    "prompt_id",
    "secret",
    "server",
    "token",
}
DROP_KEY_FORMS = {key.replace("_", "") for key in DROP_KEYS}
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


def _normalized_key(key: object) -> str:
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", str(key).strip())
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")


def _sensitive_key(key: object) -> bool:
    normalized = _normalized_key(key)
    compact = normalized.replace("_", "")
    return (
        compact in DROP_KEY_FORMS
        or normalized.endswith("_api_key")
        or normalized.endswith("_secret_access_key")
        or normalized.endswith("_access_key")
        or normalized.endswith("_access_token")
        or normalized.endswith("_token")
        or normalized.endswith("_client_secret")
        or normalized.endswith("_secret")
        or normalized.endswith("_password")
    )


def _has_credential_assignment(value: str) -> bool:
    return any(_sensitive_key(match.group("name")) for match in ASSIGNMENT_RE.finditer(value))


def _contains_private_ip(text: str) -> bool:
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
            return True
    return False


def _sensitive_string(value: str) -> bool:
    return bool(
        HOME_PATH_RE.search(value)
        or EMAIL_RE.search(value)
        or _contains_private_ip(value)
        or _has_credential_assignment(value)
        or BEARER_RE.search(value)
        or PRIVATE_KEY_MARKER in value
    )


def clean(value):
    """Recursively drop sensitive fields and redact suspicious string values."""
    if isinstance(value, dict):
        return {
            key: clean(item)
            for key, item in value.items()
            if not _sensitive_key(key)
        }
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, str) and _sensitive_string(value):
        return REDACTED
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    sanitized = clean(data)
    args.output.write_text(
        json.dumps(sanitized, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
