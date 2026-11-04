# Usage — intro-related-work

Challenge id: `product-arena-04-4b82ad21`.

## Method

`audit_intro.py` checks a draft against a library you supply:

- every paper id is in exactly one group
- every cell quote is a whitespace-normalized substring of that paper's `text`, unless `not_reported` is true
- gap premises are known paper ids, or the gap is flagged `author_judgment`
- each contribution lists `evidence_ids` that exist in the inventory
- prose cites of the form `[@id]` resolve to a paper or an evidence id

The script does not write the prose. It refuses unbound comparisons.

## Commands

```bash
python3 scripts/audit_intro.py --case /input/case.json --input-root /input \
  --work /app/work --output /app/output/result.json
python3 scripts/run_example.py
```

## Limits

- Fairness of a paraphrase in `claim` is not scored beyond the quote being real.
- Papers with empty `text` cannot support a cell. Mark `not_reported` or paste the passage you actually have.
- This skill does not search the web for extra related work.
