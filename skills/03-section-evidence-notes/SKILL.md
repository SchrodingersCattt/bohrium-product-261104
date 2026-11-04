---
name: section-evidence-notes
description: >
  Turn a paper into section-aligned note cards whose quotes are substrings of
  that section. Use for structured reading notes, paper cards, or evidence-linked
  summaries of question, data, method, finding, and limitation.
---

# Section-aligned reading notes

Challenge: `product-arena-06-6d8cf72b` (阅读10｜文献总结与结构化笔记).

Sharp sub-problem: notes follow the paper's own headings, and every quote is a substring of that section. The five fields are `question`, `data`, `method`, `finding`, and `limitation`. A missing field is a gap, not a sentence you invent.

## Procedure

1. Read `/input/case.json` and the paper. If it is a PDF, use extracted text with section breaks. Do not paste a generic abstract template over the paper's headings.
2. Draft `notes.json` with `cards[]`: `card_id`, `section_id` or `section_title`, `field`, `text`, `evidence_quote`. The quote is copied from that section, not paraphrased into the quote field. The paraphrase, if any, goes in `text`.
3. Audit:

```bash
python3 /skills/weekly-skill/scripts/audit_notes.py \
  --case /input/case.json --input-root /input \
  --notes /app/work/notes.json \
  --work /app/work --output /app/output/result.json
```

4. Repair cards named in `uncertainty`. Do not add a card whose quote you cannot find. If a field is absent from the paper, leave it in `field_gaps`.
5. Validate with `scripts/validate_result.py` and `resources/output_contract.json`.

## result.json

Envelope plus `paper`, `sections` (id, title, level, text), `cards`, `knowledge_points`, `field_gaps`.

`knowledge_points` keeps only cards whose quote matched. Duplicate field-plus-quote pairs are rejected.

`status` is `partial` when any quote misses its section or a required field has no anchored card. `success` means all five fields have a matching quote.

## Failure rules

- Unknown section id: that card does not count.
- Quote not in the section after whitespace collapse: the card does not count. Do not widen the quote to the whole paper.
- Two cards with the same field and the same quote: the second is a duplicate.
- Scanned pages you cannot read: say so in `limits`. Do not borrow a finding from the abstract to fill Methods.

## Example

`examples/minimal/paper.md` is a five-section toy. It is not an official case. `run_example.py` checks that changing `0.50` to `0.99` fails the audit.
