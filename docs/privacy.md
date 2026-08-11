# Public sharing and privacy checklist

Run the automated tracked-file gate first:

```bash
python tools/check_public_content.py
```

Then inspect the full working tree manually. These checks are intentionally
separate so their quantifiers cannot cross alternation branches:

```bash
# Unix and Windows home-directory paths
rg -n --hidden --glob '!.git' '/(home|Users)/[A-Za-z0-9._-]+|[A-Za-z]:[\\/]Users[\\/][A-Za-z0-9._-]+' .

# Private or local address candidates; review matches manually
rg -n --hidden --glob '!.git' '\b(10\.|127\.|169\.254\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)' .

# Email-like identifiers
rg -n --hidden --glob '!.git' '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' .

# Common secret-like material
rg -n --hidden --glob '!.git' '(api[_-]?key|authorization|secret|token|password|BEGIN .* PRIVATE KEY)' .
```

Review every match manually. A scanner cannot determine whether a prompt,
filename, model card, URL, or embedded workflow note contains personal data.

Model weights, generated media, raw logs, and JSONL traces must not be committed.
The only binary runtime-data exception is the audited Turbo time-conditioning
grid documented in `vendored-components.json`; CI verifies its exact path and hash.

The public repository should contain only neutral examples and synthetic test
prompts. Keep private benchmark evidence in a separate local archive.
