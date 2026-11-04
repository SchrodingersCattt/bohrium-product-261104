---
name: latex-compile-hygiene
description: >
  Compile a LaTeX manuscript with pdflatex and map log errors to file and
  line, while flagging undefined or uncited figure and table labels. Use for
  LaTeX writing, template builds, or compile-error repair.
---

# LaTeX compile and label hygiene

Challenge: `product-arena-07-865de7e4` (写作13｜LaTeX 写作与编译).

Sharp sub-problem: the `.tex` is compiled with `pdflatex`, and a failure is reported with the log's file and line. Figure and table labels are checked locally: undefined `fig:` / `tab:` references and floats that are never referenced. This skill does not treat a DOCX converter as a compiler. It does not ship doc-forge. The label check is a small original gate with the same idea as a figure/table reference audit: defined labels, references, and uncited floats.

## Procedure

1. Read `task.md` and the main file named by the case (`materials.main`, default `main.tex`). Keep the template's `documentclass`. Do not replace the project with a fragment that only looks like LaTeX.
2. Run:

```bash
python3 /skills/weekly-skill/scripts/compile_tex.py \
  --case /input/case.json --input-root /input \
  --work /app/work --output /app/output/result.json
```

The script copies sibling `.tex`, `.bib`, `.cls`, and `.sty` files into `/app/work/build` and runs `pdflatex -interaction=nonstopmode -halt-on-error`. A second pass runs only if the first pass wrote a PDF.

3. Read `errors[]` (`file`, `line`, `message`) and `hygiene[]`. Fix the source, then compile again. Prefer the first line-mapped error. Do not stop at a vague "it failed".
4. Uncited `tab:` or `fig:` labels are hygiene notes. Either reference them or remove the float. Do not silence the note by deleting the audit.
5. If `pdflatex` is missing, `status` is `undetermined`. Do not claim a PDF. Validate with `scripts/validate_result.py`.

## result.json

Envelope plus `main_file`, `compile` (`engine`, `passes`, `exit_code`, `pdf`), `errors`, `hygiene`, `artifacts` (`log_tail`, `pdf_written`).

`status` is `partial` when the engine returns non-zero or hygiene still has notes. `success` means both passes (when a PDF exists) finished and the label gate is clean. The PDF path is under the work build directory. The skill bundle itself stays text.

## Failure rules

- Missing main file: `refused`.
- Undefined control sequence: cite `file` and `line` from the log. Do not guess a package without reading the error.
- `\cite` keys with no `.bib` beside the main file: hygiene `missing_bib` or `unknown_cite`. Do not invent BibTeX entries.
- A fatal error means `pdf_written` is false. Do not point reviewers at a stale PDF.

## Example

`examples/minimal/main.tex` compiles and leaves `tab:unused` uncited. `broken.tex` fails on `\blurb` at line 4. Not an official case. `run_example.py` checks both.
