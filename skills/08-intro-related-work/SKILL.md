---
name: intro-related-work
description: >
  Draft introduction and related-work material as a comparison table whose
  quotes come from the cited papers and whose contributions point at an
  evidence inventory. Use for related work, research gaps, or contribution
  statements.
---

# Related work bound to quotes

Challenge: `product-arena-04-4b82ad21` (写作08｜引言与相关工作写作).

Sharp sub-problem: group prior papers on an explicit axis, copy the comparison quote from that paper, and tie each contribution to an evidence id that the case actually supplies. A gap is either grounded in those premises or marked `author_judgment`. It is not a sentence about the field in general.

## Procedure

1. Build or read `library.json`:

```json
{
  "papers": [{"paper_id": "p1", "title": "", "year": 2020, "text": "verbatim passage you may quote"}],
  "inventory": [{"evidence_id": "e1", "kind": "method", "text": "from this manuscript's method or result"}]
}
```

`text` must be copied from the source you were given. If the case only has PDFs, extract the passages first and store them here. Do not quote from memory.

2. Write `draft.json`:

- `groups[]`: `group_id`, `axis`, `paper_ids`, `cells[]` with `paper_id`, `claim`, `quote`. Use `not_reported: true` when the paper does not speak to that axis. Every paper appears in exactly one group.
- `gap`: `text`, `premise_ids`, and `author_judgment` true when the gap sentence is your inference rather than a quotation.
- `contributions[]`: `text`, `evidence_ids` that exist in the inventory.
- `prose`: optional. Citations look like `[@p1]` or `[@e1]` and must be known ids.

3. Audit:

```bash
python3 /skills/weekly-skill/scripts/audit_intro.py \
  --case /input/case.json --input-root /input \
  --draft /app/work/draft.json \
  --work /app/work --output /app/output/result.json
```

4. Repair every item in `uncertainty`. A cell whose quote is not in that paper is invalid. Do not move the quote to a different paper to save the sentence.
5. Validate with `scripts/validate_result.py`.

## result.json

Envelope plus `groups`, `gap`, `contributions`, `prose`, `citation_coverage`.

`status` is `partial` when any paper is ungrouped, a quote misses, or a contribution lacks inventory evidence. If `draft.json` is absent, the script builds one group whose quote is the paper's own first sentence, marks the gap `author_judgment`, and copies one inventory passage into the contribution. `success` means the table, the gap flag, and the contributions all point at supplied text.

## Failure rules

- Missing library: `refused`.
- Unknown paper id or evidence id: listed, not silently dropped from the prose.
- Do not write "widely studied" as a substitute for a group.
- Do not claim a result that is not in the inventory.

## Example

`examples/minimal/` uses two fictional prior notes and one method evidence id. `run_example.py` rejects a quote the paper does not contain. Not an official case.
