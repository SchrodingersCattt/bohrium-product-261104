---
name: nanopub-assertions
description: >
  Split a paper into single-claim spans and audit nanopublication records
  against a controlled relation list and in-span quotes. Use for
  nanopublications, claim extraction, or evidence binding.
---

# Nanopublication span audit

Challenge: `product-arena-09-0e8befd4` (阅读14｜Nanopublication).

Sharp sub-problem: one assertion per span, with the evidence quote inside that span. A paragraph that joins two claims with `;` or `while` / `whereas` becomes two spans. A span that is not a claim is rejected with a reason. It is not dropped silently.

Read `resources/assertion_patterns.jsonl` (20 fictional Widget shapes) and `resources/relations.json` before writing assertions. Those patterns are not contest answers.

## Procedure

1. Read the source named by `/input/case.json`.
2. Write `assertions.json`. If that file is absent, the script still emits `result.json`: spans whose case states `paper_provenance` (`source_id`, `title`, `authors`, `year`) become one direct assertion when a controlled relation word is in the span; every other span is an explicit rejection. Provenance is not invented.

- `paper_provenance`: `source_id`, `title`, `authors`, `year`, and version or identifier when the paper states them.
- `assertions[]`: `assertion_id`, `span_id`, `subject`, `relation`, `object`, `conditions`, `assertion_text`, `evidence_quote`, `evidence_kind` (`direct` or `inference`), `confidence`, `confidence_basis`, `provenance` with the same identity fields.
- `rejected_spans[]`: `{span_id, reason}` for spans you will not turn into a claim.

Use a relation from `resources/relations.json`. If you must use another verb, set `relation_status` to `proposed`. The subject string must occur in the quote. Do not put two spans in one assertion. Do not put `;` in `assertion_text`.

3. Audit:

```bash
python3 /skills/weekly-skill/scripts/audit_nanopub.py \
  --case /input/case.json --input-root /input \
  --assertions /app/work/assertions.json \
  --work /app/work --output /app/output/result.json
```

4. The script writes `spans.json` first in spirit: it recomputes spans from the source. Your `span_id`s must match that split (`sp1`, `sp2`, ...). Open `/app/work/spans.json` after a run and fix ids if the split differs from your draft.
5. Validate with `scripts/validate_result.py`.

## result.json

Envelope plus `provenance`, `spans`, `assertions`, `rejected_spans`, `quality_checks`.

`status` is `partial` when any check fails or a span is unaccounted. A proposed relation also forces `partial`. `success` means every span is one controlled assertion or an explicit rejection, and each quote sits inside its span.

## Failure rules

- Quote not in the span: fail that assertion. Do not point at a different paragraph to rescue it.
- Missing provenance field: fail. Do not copy another paper's year.
- Subject absent from the quote: fail (`subject_not_in_evidence`).
- No text layer: `refused` or `undetermined`. Do not mint claims.

## Example

`examples/minimal/source.md` is one toy sentence plus a non-claim. `run_example.py` checks that a semicolon-joined assertion is marked `too_wide` and that leftover spans are `span_not_accounted`.
