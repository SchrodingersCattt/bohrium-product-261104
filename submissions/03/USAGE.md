# Usage — section-evidence-notes

Challenge id: `product-arena-06-6d8cf72b`.

## Method

`audit_notes.py` splits the source on Markdown headings or numbered headings (`1.2 Title`). Cards must name that `section_id`. `evidence_quote` must be a whitespace-normalized substring of that section only. Required fields are question, data, method, finding, and limitation.

The script does not summarize. It accepts or rejects the notes you wrote.

## Commands

```bash
python3 scripts/audit_notes.py --case /input/case.json --input-root /input \
  --work /app/work --output /app/output/result.json
python3 scripts/run_example.py
```

## Limits

- Heading detection is line-based. A PDF with no heading lines should be given a text file that already marks sections, or the preamble becomes one section and you must say the outline is uncertain.
- The checker does not judge whether a paraphrase in `text` is fair beyond the quote being real.
