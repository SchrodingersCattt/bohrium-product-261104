# Usage — methods-from-config

Challenge id: `product-arena-05-64faa4a2`.

## Method

`audit_methods.py` walks a config file or directory. It reads JSON scalars and lines of the form `name: value` or `name=value`. The prose is scanned for numbers. A number is supported when its token, or `str(float(token))`, appears among the extracted values. Dataset-like keys (`dataset`, `data`, `split`, `train_split`, `test_split`, or a name containing `dataset`) fill `datasets`. If none exist, the dataset entry is `not_in_source` and the run stays `partial`.

The script does not write the scientific narrative. It builds the table and rejects unsupported numerals.

## Commands

```bash
python3 scripts/audit_methods.py --case /input/case.json --input-root /input \
  --work /app/work --output /app/output/result.json
python3 scripts/run_example.py
```

## Limits

- The line parser is not a full YAML loader. Nested blocks and anchors are ignored.
- Units are not inferred. Put the unit in prose only when the config value includes it or you mark the unit as not from the file.
- Logs that print a number without `key: value` syntax are not picked up.
