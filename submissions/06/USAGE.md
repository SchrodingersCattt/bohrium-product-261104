# Usage — academic-polish-ledger

Challenge id: `product-arena-02-7051d92d`.

## Method

`audit_edits.py` splits the source into sentences and applies an edit only when:

- `original` equals the source sentence
- the number tokens match
- unit surfaces such as `10 mg/L` match after spaces are removed
- bracket citations, `\cite{...}`, and `(Author, 2020)` match
- `Figure` / `Fig.` / `Table` / `图` / `表` numbers match
- a weak hedge in the source is not replaced by a strong verb
- `correlation` is not rewritten as `cause`
- `edit_type` is in the allowed set and `reason` is non-empty

Failed edits stay at the original sentence. The ledger records both applied edits and reverts.

This skill does not generate Word tracked changes. The graded artifact is `result.json`.

## Commands

```bash
python3 scripts/audit_edits.py --case /input/case.json --input-root /input \
  --work /app/work --output /app/output/result.json
python3 scripts/run_example.py
```

## Limits

- Sentence boundaries are punctuation. Abbreviations such as `Fig.` can split a sentence early; if that happens, set `uncertainty` and edit the pieces the script actually produced.
- The hedge list is small and English-first. A Chinese hedge you care about should be preserved by not editing that token, and noted in the reason.
- Style preferences that do not trip these checks are your judgment. The script will not invent a journal's house style.
