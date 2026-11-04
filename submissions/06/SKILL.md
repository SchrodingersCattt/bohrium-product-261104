---
name: academic-polish-ledger
description: >
  Polish academic sentences with an edit ledger and revert any edit that
  changes numbers, units, citations, figure references, or hedge strength.
  Use for academic language polishing or sentence-level revision logs.
---

# Academic polish with a preservation ledger

Challenge: `product-arena-02-7051d92d` (写作02｜学术语言润色).

Sharp sub-problem: sentence-level edits that cannot silently strengthen a claim or drop a number. The model proposes the wording. The script keeps or reverts each sentence.

## Procedure

1. Read the source from `/input/case.json` (`materials.source` or inline `text`).
2. Write `edits.json`. One object per sentence you touch:

```json
{"sentence_id": "s1", "original": "...", "revised": "...", "edit_type": "grammar", "reason": "..."}
```

`sentence_id` follows the script's split: `s1`, `s2`, ... in order, splitting after `.`, `!`, or `?`. `original` must match that sentence including its closing punctuation. `edit_type` is one of `grammar`, `punctuation`, `terminology`, `register`, `clarity`, `structure`, `unchanged`. `reason` is required.

3. Do not remove `may` / `might` / `suggest` and replace them with `prove` / `demonstrate` / `clearly`. Do not turn correlation into causation. Do not change numbers, units (`10 mg/L`), bracket citations, or `Figure` / `Table` numbers.

4. Run:

```bash
python3 /skills/weekly-skill/scripts/audit_edits.py \
  --case /input/case.json --input-root /input \
  --edits /app/work/edits.json \
  --work /app/work --output /app/output/result.json
```

5. `revised_text` uses the revised sentence only when the checks pass. Failed edits are reverted and listed in `change_records` with action `revert`. Fix the proposal and run once more if you still want a wording change. Validate with `scripts/validate_result.py`.

## result.json

Envelope plus `revised_text`, `edits` (`applied` true or false), `preservation` (numbers and citations per source sentence), `sentences`.

`status` is `partial` when any edit was reverted. If `edits.json` is absent, each sentence is recorded as `unchanged` and `success` means that verbatim ledger passed the preservation checks. A present edits file is `success` when every proposed edit passed.

## Failure rules

- `original` that does not match the source sentence: reverted.
- Number, unit, citation, or figure/table mismatch: reverted.
- Hedge strengthened, or correlation rewritten as cause: reverted.
- Missing source file: `refused`.

## Example

`examples/minimal/source.txt` keeps `may`, `10 mg/L`, `[1]`, and `Figure 1`. `run_example.py` checks that swapping `may` for `proves` is reverted. Not an official case.
