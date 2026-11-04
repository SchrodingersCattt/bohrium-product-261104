---
name: literature-term-lock
description: >
  Translate a research paper segment by segment with a locked glossary and
  checks that numbers, units, citations, and formulas survive. Use for
  literature translation, bilingual alignment, or terminology consistency.
---

# Literature translation with a locked glossary

Challenge: `product-arena-01-5a9928c1` (阅读03｜文献翻译).

Sharp sub-problem: paragraph alignment plus hard checks. The model writes the translation. The scripts decide whether a segment kept its numbers, units, citation surfaces, formulas, and locked terms. Do not translate a whole paper in one reply.

## Layout

Skill root: directory of this file, normally `/skills/weekly-skill`.

Inputs: `/input/case.json`, `/input/task.md`, and the source file named by the case. Work in `/app/work`. Write `/app/output/result.json`.

Budget: 64 model requests, 900 seconds, 16384 tokens per response. Translate a batch of segments per request, then audit. Fix only the segments the audit lists.

## Procedure

1. Read the case and the source file. Do not invent measurements from a domain label.
2. Segment the source:

```bash
python3 /skills/weekly-skill/scripts/segment_source.py \
  --case /input/case.json --input-root /input \
  --output /app/work/segments.json
```

3. Build `glossary.json`. Lock a term only if it appears in the source. `entries[]` has `source`, `target`, `locked`. Add `unit_maps` only when `task.md` asks for translated unit names. Otherwise keep the SI symbol.
4. Write `translation.json` with the same `seg_id`s. One translation per segment. Copy citation surfaces and `$...$` formulas verbatim. Keep every number token.
5. Audit:

```bash
python3 /skills/weekly-skill/scripts/audit_translation.py \
  --case /input/case.json --input-root /input \
  --segments /app/work/segments.json \
  --glossary /app/work/glossary.json \
  --translation /app/work/translation.json \
  --work /app/work --output /app/output/result.json
```

6. If `audit.issues` is non-empty, rewrite only those segments and audit once more. Then validate:

```bash
python3 /skills/weekly-skill/scripts/validate_result.py \
  /app/output/result.json \
  --contract /skills/weekly-skill/resources/output_contract.json \
  --case /input/case.json
```

## result.json

Envelope: `case_id`, `status`, `status_reason`, `sources`, `uncertainty`, `change_records`, `limits`.

Track fields: `source_language`, `target_language`, `glossary`, `segments` (source, translation, issues), `audit`.

`status` is `partial` when any segment fails a lock or the translation file is missing. `success` means every segment passed. Do not mark success to hide a dropped numeral.

## Failure rules

- Missing source: the segmenter raises; report `refused` if you cannot read the file.
- A segment with no translation stays `partial`. Do not fill it with a summary of neighboring segments.
- Locked term missing, number multiset mismatch, missing citation surface, missing formula, or missing unit: that segment fails.
- Fullwidth parentheses are normalized before the citation check. Digits are not.
- If the source is a scan with no text, stop and say so. Do not translate a guessed OCR string.

## Example

`examples/minimal/` is a toy English paragraph. It is not an official case. `scripts/run_example.py` also checks that dropping `10` and the locked term is caught.
