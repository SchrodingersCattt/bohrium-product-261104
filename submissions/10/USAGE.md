# Usage — latex-compile-hygiene

Challenge id: `product-arena-07-865de7e4`.

## Method

`compile_tex.py` does two text-only jobs:

1. Hygiene, before and beside the compile. Comments are stripped. `\label{fig:...}` and `\label{tab:...}` must be unique. `\ref` to those prefixes must exist. A float label that is never referenced is `uncited_float`. `\cite` keys are checked against `.bib` files in the same directory. The file must contain `\documentclass`, `\begin{document}`, and `\end{document}`.
2. Compile. `pdflatex` runs in a work directory with `-output-directory`. The log parser keeps the latest `.tex` file opened in the log and attaches the next `l.<number>` line to the preceding `!` error. Citation and undefined-reference warnings are kept even when they have no line.

A second pass runs only after a PDF exists, so reference warnings can settle. The engine is pdflatex, not a DOCX converter.

## Commands

```bash
python3 scripts/compile_tex.py --case /input/case.json --input-root /input \
  --work /app/work --output /app/output/result.json
python3 scripts/run_example.py
```

## Dependencies

`pdflatex` on `PATH`. No extra Python packages. If the binary is absent the hygiene list is still written and `status` is `undetermined`.

## Limits

- The log parser reports the line TeX prints. A runaway argument can point at the wrong line; keep the log tail.
- `sec:` and `eq:` labels are not required to be referenced. The gate is figures and tables.
- Bibliography style files and journal classes must already be on the TeX path or beside the main file. This skill does not download them.
- The simplified gate does not compile BibTeX itself. A missing `.bbl` still shows up as a pdflatex warning in `errors`.
