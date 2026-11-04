# Usage — literature-term-lock

Challenge id: `product-arena-01-5a9928c1`.

## Method

`segment_source.py` splits the source on blank lines and records, per segment: numbers, number-unit pairs, citation surfaces (`\cite`, `[n]`, `(Author, 2020)`), `$...$` formulas, abbreviations, and lowercase term candidates.

`audit_translation.py` requires one translation per `seg_id`. It fails a segment when the number multiset differs, a citation or formula surface is missing, a unit symbol is missing and not mapped, or a `locked` glossary entry's target string is absent. Extra segment ids are also failures.

The model chooses the wording. The scripts do not call a translation API.

## Commands

```bash
python3 scripts/segment_source.py --case /input/case.json --input-root /input --output /app/work/segments.json
python3 scripts/audit_translation.py --case /input/case.json --input-root /input \
  --work /app/work --output /app/output/result.json
python3 scripts/run_example.py
```

## Glossary file

```json
{"entries": [{"source": "binding affinity", "target": "结合亲和力", "locked": true}], "unit_maps": []}
```

## Limits

- Terminology is locked only after it is written into `glossary.json`. Candidates are hints, not translations.
- The checker does not judge fluency or omitted hedges beyond the locked tokens.
- Paragraph boundaries follow blank lines. A PDF should be segmented from extracted paragraphs first; this skill does not rebuild column order.
