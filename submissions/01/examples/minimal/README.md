# Minimal example (not a contest case)

This folder is a labeled interface example. It is not an official case, not a whiteboard, and not a prepared answer.

Input: `case.json`, `task.md`, `fixture_spec.json` (text boxes with the same shape as an OCR handoff).

Run from the skill root:

```bash
python3 scripts/run_example.py
```

`example_result.json` is the script output for this fixture, labeled example-only. Official cases supply a real PDF at `/input` and are not stored here.
