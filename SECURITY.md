# Security and privacy

## Private vulnerability reports

Do not publish credentials, private prompts, private media, mailbox data, or
machine-identifying logs in an issue.

Use GitHub's private vulnerability reporting for this repository:

https://github.com/JH427/minimax-h3-comfyui-acceleration/security/advisories/new

Include the affected commit, component, reproduction conditions, and impact, but
remove private paths, endpoints, prompts, and generated media.

## Public benchmark artifacts

Before sharing a benchmark artifact:

1. Run `python tools/sanitize_manifest.py INPUT OUTPUT`.
2. Inspect the sanitized output manually.
3. Run `python tools/check_public_content.py` on the tracked tree.
4. Remove credentials, local paths, hostnames, private IP addresses, queue IDs,
   prompt IDs, private prompts, and personal data.

The sanitizer and scanner are defense-in-depth tools, not a substitute for human
review.
