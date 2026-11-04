# Usage — nanopub-assertions

Challenge id: `product-arena-09-0e8befd4`.

## Method

`audit_nanopub.py` splits text into sentences, then splits a sentence on `;` or on `while` / `whereas`. Each span must be named by an assertion or by `rejected_spans`. Relations must be in `resources/relations.json` unless `relation_status` is `proposed`. The evidence quote must be a substring of that span. The subject must appear in the quote. `evidence_kind` is `direct` or `inference`. Provenance on each assertion needs `source_id`, `title`, `authors`, and `year`.

`resources/assertion_patterns.jsonl` has 20 fictional shape examples. They are labeled `example_only`.

## Commands

```bash
python3 scripts/audit_nanopub.py --case /input/case.json --input-root /input \
  --work /app/work --output /app/output/result.json
python3 scripts/run_example.py
```

## Limits

- The splitter is punctuation-based. A claim hidden in a compound noun is not split further.
- The script does not decide scientific truth. It decides shape, span coverage, and whether the quote is actually in the span.
- Confidence is your number plus a one-line basis. The script does not score it.
