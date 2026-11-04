---
name: methods-from-config
description: >
  Write method and experiment prose whose numbers come from config files and
  logs, and flag any number or dataset the files do not contain. Use for
  methods sections, experimental settings, or reproducibility checklists.
---

# Methods prose traced to config

Challenge: `product-arena-05-64faa4a2` (写作09｜方法与实验章节写作).

Sharp sub-problem: a parameter table with file and line, and a prose audit that flags numbers the config does not contain. Missing datasets stay `not_in_source`. They are not filled in to make the paragraph smooth.

## Procedure

1. Read the config directory or file from the case (`materials.config` or `materials.config_dir`). JSON objects and `key: value` / `key=value` lines in `.yaml`, `.yml`, `.txt`, and `.log` are extracted. Nested JSON objects are skipped rather than flattened into guesses.
2. Write `prose.md` using only values that appear in that table. If you mention a dataset, its name must be one of the extracted values. If the config has no dataset key, say the dataset is not in the source.
3. Run:

```bash
python3 /skills/weekly-skill/scripts/audit_methods.py \
  --case /input/case.json --input-root /input \
  --prose /app/work/prose.md \
  --work /app/work --output /app/output/result.json
```

4. `number_audit.unsupported` lists numbers to remove or to trace. Do not add a config line that was not in the file. If a command, seed, or environment variable is absent, leave it out of the prose and keep the limitation.
5. Validate with `scripts/validate_result.py`.

## result.json

Envelope plus `parameter_table` (name, value, source path, line), `datasets`, `steps`, `prose`, `number_audit`, `reproducibility`, `limitations`.

`reproducibility.command` is copied from the case when the case provides `command`. An empty command means the case did not give one.

`status` is `partial` when prose contains an unknown number or a setup field such as the dataset is absent. `undetermined` when no key-value pairs were found. `success` means every prose number is in the table and the dataset field was present in the files. `refused` when the config path does not exist.

## Failure rules

- Do not invent epoch counts, seeds, split ratios, or dataset names.
- A number used as a section label still counts. Avoid numbered section titles in the prose, or the audit will flag them.
- Hardware that is not in the config is a limitation, not a guessed GPU name.

## Example

`examples/minimal/config.yaml` has `seed`, `lr`, and `epochs` and no dataset. The toy prose uses only those three numbers. `run_example.py` checks that `99` is flagged. Not an official case.
