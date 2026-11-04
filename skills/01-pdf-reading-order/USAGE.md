# Usage — pdf-reading-order

Challenge id: `product-arena-08-3027d350`.

## What the script does

`scripts/parse_pdf.py` turns a PDF, or a JSON file of text boxes, into ordered blocks. It does not summarize. Column order uses left-edge clusters so a short line stays in its column. Full-width lines (at least 72% of the content width) break the page into bands and are emitted when their vertical position says so. Headers and footers in the outer 6.5% of the page are kept on the page record and marked `in_body_flow: false`.

PyMuPDF `find_tables` supplies table rows when it runs. Cell text is the finder's text, not a guess. Formula roles are surface patterns (`E = mc^2`, dense operator characters). They are not interpreted.

`pdftotext -layout` is the fallback. That mode has no coordinates, so `status` is `partial` and column order is not claimed.

## Inputs

- `case.json` fields: `case_id`, `materials.pdf` or `materials.fixture`, optional `output_contract`.
- Fixture shape: `pages[].{page,width,height,blocks[]}`; each block has `bbox` `[x0,y0,x1,y1]`, `text`, optional `size`.
- OCR handoff uses that same fixture shape. This skill does not run Tesseract itself.

## Outputs

`/app/output/result.json` as described in `SKILL.md`. `scripts/validate_result.py` checks the envelope plus any extra `output_contract` names on the case.

## Command

```bash
python3 scripts/parse_pdf.py --case /input/case.json --input-root /input \
  --work /app/work --output /app/output/result.json
python3 scripts/validate_result.py /app/output/result.json \
  --contract resources/output_contract.json --case /input/case.json
```

Local example:

```bash
python3 scripts/run_example.py
```

## Roles

`resources/roles.md` lists allowed roles: `header`, `footer`, `heading`, `paragraph`, `caption`, `table`, `formula`, `reference`.

## Limits

- Reading order is geometric. A text layer that is already scrambled inside a single line cannot be repaired.
- Scans without a text layer are `undetermined` until boxes are supplied.
- Merged cells and multi-row headers are only as good as `find_tables` on that page. Failures are warnings, not filled-in values.
- No network, no invented DOI, no invented sentence.

## Self-check

On the minimal fixture, body order contains `LEFT-ANCHOR` before `RIGHT-ANCHOR`, `Example Journal` is not in the body flow, and `E = mc^2` is a formula span. `run_example.py` also renders the fixture to a PDF and checks the same invariants.
