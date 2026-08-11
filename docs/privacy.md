# Public sharing and privacy checklist

Before committing or publishing:

```bash
# Paths, private addresses, and email-like identifiers
rg -n --hidden --glob '!.git' --glob '!*.lock' \
  '(/home/|/Users/|[0-9]{1,3}\.){3}[0-9]{1,3}|@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' .

# Common secret-like material
rg -n --hidden --glob '!.git' \
  '(api[_-]?key|secret|token|password|BEGIN .* PRIVATE KEY)' .

# Artifacts that should never be committed
find . -type f \( -name '*.safetensors' -o -name '*.mp4' -o -name '*.log' -o -name '*.jsonl' \) -print
```

Review the output manually. Do not assume a scanner understands whether a
prompt, image, filename, or model card contains personal data.

The public repository should contain only neutral examples and synthetic test
prompts. Keep private benchmark evidence in a separate local archive.
