# Contributing

Keep changes small and reproducible.

## Before opening a pull request

```bash
python -m pytest -q tests/test_benchmark_graph.py
python -m compileall -q tools tests
```

Run the privacy checklist in `docs/privacy.md`. Do not submit model weights,
private prompts, generated media containing identifiable people, raw local logs,
private IP addresses, absolute home-directory paths, or credentials.

For performance claims, include:

- exact lane and settings;
- measured wall-clock time;
- frame count and FPS;
- hardware/runtime class;
- control comparison;
- validation status;
- limitations.

Do not present a projection as a measurement.
