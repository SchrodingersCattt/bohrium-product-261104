---
name: pdf-reading-order
description: >
  Parse a research PDF into page-anchored blocks in column reading order,
  with headers, tables, and formula spans kept traceable to the text layer.
  Use when the task is literature document parsing, multi-column reading
  order, or structured extraction that must not invent text.
---

# PDF reading order

Challenge: `product-arena-08-3027d350` (阅读01｜文献文档解析).

Sharp sub-problem: recover body reading order on multi-column pages and label headers, headings, captions, tables, and formula surface text. Do not build a general PDF platform. Do not interpret the science. Every emitted character must come from the text layer or from an OCR box file the platform already produced.

## When this applies

Use this skill when `/input` contains a research PDF, a scan plus OCR boxes, or a task that asks for structured text, sections, tables, or formula spans with page locations.

## Layout

Installed skill root is the directory of this file, normally `/skills/weekly-skill`.

| Path | Role |
|---|---|
| `/input/case.json` | Case id, material paths, optional `output_contract` |
| `/input/task.md` | What to return |
| `/app/work` | Scratch |
| `/app/output/result.json` | Final contract |

Write a partial `result.json` as soon as the parser finishes, then edit only role labels you can justify. Do not spend the 64-request / 900s budget re-typing the paper.

## Procedure

1. Read `case.json` and `task.md`. Resolve the PDF path from the case. Do not assume the paper's topic from a domain tag.
2. Run:

```bash
python3 /skills/weekly-skill/scripts/parse_pdf.py \
  --case /input/case.json \
  --input-root /input \
  --work /app/work \
  --output /app/output/result.json
```

3. The script uses PyMuPDF line boxes when that import works, otherwise `pdftotext -layout`. Line boxes are required because MuPDF often glues two columns into one block. Reading order is: full-width bands in vertical order; inside a band, clusters of left edges from left to right, each cluster top to bottom. Wrapped lines join only when they share a left edge and sit within 3.5pt. Headers and page numbers in the top or bottom 6.5% margin are labeled and removed from the body flow, not deleted.
4. If the text layer is empty, stop. Set `status` to `undetermined`. Do not guess characters. If an OCR tool returns boxes, save them as a fixture (`pages[].blocks[].bbox/text/size`) and rerun with `materials.fixture`. The same orderer consumes that file.
5. Optional model pass, only for blocks with `role_confidence` below 0.6: relabel `role` using `resources/roles.md`. You may not change `text` or `raw_text`. If a line-end hyphen was joined, keep `raw_text` and list the block under `uncertainty`.
6. If `task.md` asks a question, add `answers[]` with `claim`, `block_ids`, and a `quote` copied from those blocks. If the blocks do not contain the answer, say `undetermined` for that item.
7. Validate:

```bash
python3 /skills/weekly-skill/scripts/validate_result.py \
  /app/output/result.json \
  --contract /skills/weekly-skill/resources/output_contract.json \
  --case /input/case.json
```

## result.json

Envelope: `case_id`, `status` (`success` | `partial` | `undetermined` | `refused`), `status_reason`, `sources`, `uncertainty`, `change_records`, `limits`.

Track fields:

- `document` — path, backend, page and block counts
- `blocks[]` — `block_id`, `page`, `reading_index`, `in_body_flow`, `bbox`, `column`, `role`, `role_confidence`, `text`, `raw_text`
- `sections[]` — heading title, level, page, member block ids
- `tables[]` — page, bbox, rows (cells from the text layer only)
- `formulas[]` — surface text and page; no derived meaning
- `reading_order_notes[]` — per-page column mode and split positions
- `unreadable[]` — image-only or failed pages

`status` is `partial` when some pages have no coordinates or no text layer. `refused` when the file is missing or encrypted and no password was supplied.

## Failure rules

- Missing PDF: `refused`, empty block lists, name the path you looked for.
- Encrypted PDF: `refused`. Do not claim you read it.
- Image-only page: record it in `unreadable`. Do not copy a caption from a neighboring page to fill it.
- Table cells that the table finder cannot read stay empty strings. Do not fill them from memory.
- Dehyphenation is uncertain. Prefer `raw_text` when a join looks wrong (`well-known` split across a line).

## Budget

One parser run plus one validation is the default. A second parser run is only for an OCR fixture. Do not call the model once per paragraph when the script already emitted the text.

## Example

`examples/minimal/` is a synthetic two-column fixture. The right column is higher on the page than the left column, so a pure y-sort is wrong. See `examples/minimal/README.md`. It is not an official case.
