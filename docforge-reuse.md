# Period 2 writing tracks and doc-forge

Period page: https://play.bohrium.com/competition/bohr-product?period=2
Theme: AI literature reading and academic writing.
Window shown on the period page: 2026-11-04 16:00 to 2026-11-11 16:00 (UTC+8).
Prize pool is the combined score across all ten challenges.
Each challenge is a Skill-authoring task. The platform runs official DeepSeek Harness on three fixed cases, with and without the submitted Skill. Participants do not submit prepared answers.

`GET /api/challenges/{id}` currently returns `status: closed`, and each statement ends with “题面已公开，正式提交开放时间以赛事通知为准。” The briefs below are the public statements. Submit availability still follows the contest notice.

## The ten challenges

Slots on the period page, not the topic numbers in the titles.

| Slot | Title | id | Track |
|---|---|---|---|
| 01 | 阅读01｜文献文档解析 | product-arena-08-3027d350 | reading |
| 02 | 阅读03｜文献翻译 | product-arena-01-5a9928c1 | reading |
| 03 | 阅读10｜文献总结与结构化笔记 | product-arena-06-6d8cf72b | reading |
| 04 | 阅读14｜Nanopublication | product-arena-09-0e8befd4 | reading |
| 05 | 阅读15｜文献知识图谱构建 | product-arena-10-760d1a0b | reading |
| 06 | 写作02｜学术语言润色 | product-arena-02-7051d92d | writing |
| 07 | 写作04｜参考文献与引用管理 | product-arena-03-429cc14d | writing |
| 08 | 写作08｜引言与相关工作写作 | product-arena-04-4b82ad21 | writing |
| 09 | 写作09｜方法与实验章节写作 | product-arena-05-64faa4a2 | writing |
| 10 | 写作13｜LaTeX 写作与编译 | product-arena-07-865de7e4 | writing |

Full statements are in `challenges/*.json`. Scoring on all ten is `human_review_only` (0–100): effect 40, gain vs the bare agent 25, novelty 15, reliability 10, reuse/docs 10. A run must write `/app/output/result.json` with the case `output_contract` fields, sources, uncertainty, and a change record. Budget: 64 model requests, 900 seconds, 16384 tokens per response. Skill bundle: at most 50 UTF-8 text files, 500 KB each, 2 MB total, no symlinks.

## What doc-forge actually is

https://github.com/SchrodingersCattt/doc-forge (MIT, v0.1.0). Local checkout: `vendor/doc-forge`.

It builds and audits Word documents from Markdown or a LaTeX subset. It does not write prose, and it does not compile LaTeX to PDF.

Useful pieces:

- `docforge.bibliography`: JSON and BibTeX in, citation resolution, `first-citation` or `source-order` numbering, `plain` and `markdown` reference lines. Unknown keys can fail the build. The five modules are about 20 KB and use only the standard library.
- `gate references`: undefined `fig:` / `tab:` labels, and main-text figures or tables that are never cited. It ignores `sec`, `eq`, `alg`, and does not check `\cite`.
- `gate abbr` and `gate style`: abbreviation lists, em dashes, numeric-range hyphens.
- `redline` / `apply-delta`: Word tracked changes and matched paragraph edits. This path is large (`docxdiff/redline.py` alone is about 120 KB) and needs `python-docx` and `lxml`.
- `md2docx` / `tex2docx`: manuscript to DOCX. Display math needs Pandoc 2.9.2.1, 3.1.11.1, or 3.9.0.1. Real `figure` environments are refused unless the body is literal text plus `\includegraphics`.
- `sourcepack`: an allowlisted TeX zip plus a SHA256 manifest. It does not compile.

`src/` is 78 files and about 1.3 MB. That already breaks the Skill bundle limit before dependencies and Pandoc.

## Fit by writing challenge

### 写作04 参考文献与引用管理 — reuse the bibliography package

This is the only writing track where doc-forge covers a scored mechanic rather than the file format.

Ship or call `docforge.bibliography` as a deterministic step:

- load the case `.bib` or JSON library
- resolve `\cite` / Markdown cite keys
- renumber after insert, delete, and reorder (`first-citation` or `source-order`, with range compression)
- fail closed on an unknown key
- emit a `plain` or `markdown` reference list and a key-to-number map for `result.json`

Still outside doc-forge, and still most of the 40-point effect score: where a citation belongs, whether the claim matches the paper, DOI or database checks, deduping preprint vs published and CNKI vs English titles, and styles other than `plain` / `markdown`. There is no GB/T 7714 or APA profile. `gate references` does not audit citations.

The bibliography modules fit the bundle. The rest of doc-forge does not need to come along.

### 写作02 学术语言润色 — reuse only the change record, and only for DOCX

The graded product is the revised text plus a sentence-level edit log (original, revision, edit type, reason), with hedges, numbers, units, and citation marks preserved. doc-forge does not do that editing.

`redline` is a reasonable extra when the case artifact is DOCX: the harness writes a sentence diff, and redline turns it into Word tracked changes for the office-renderer preview. Do not put the redline implementation in the Skill. It is too big, and the pinned image lists `office-renderer`, not doc-forge or Pandoc. A small sentence-diff written for `result.json` is the part the rubric asks for.

### 写作13 LaTeX 写作与编译 — do not use doc-forge as the compiler

The rubric is: the `.tex` compiles under the given template, errors map to file and line, formulas and tables match the source, and someone else can rebuild it. The platform tool for that is `latex-compiler`.

`tex2docx` targets DOCX, refuses ordinary figure markup, and the review-roundtrip docs say it does not recompile TeX. Using it as the compile loop would fail real papers and would not produce the PDF the task is judged on.

Optional, after a real compile: `sourcepack` for a hashed source zip, and `gate references` for figure and table labels. Neither fixes a TeX error.

### 写作08 and 写作09 — no meaningful reuse

引言 / 相关工作 and 方法 / 实验 are evidence-bound drafting: group prior work, derive a gap, align claims with results, and pull parameters from configs, logs, and code without inventing numbers. doc-forge has no reader or writer for that. Running `md2docx` on the finished section only changes the container.

## Recommendation

Use doc-forge for 写作04, and only the bibliography package.

Keep `vendor/doc-forge` in this folder as the source. If that challenge is the one we enter, copy `src/docforge/bibliography/` into the Skill (five text files, stdlib only) and call `CitationResolver` from the harness instructions. Document the MIT upstream and the commit. Do not `pip install` the whole package inside the 900-second eval unless `environment/resources.yaml` shows it is already on the image; that file is not in the public challenge JSON.

Leave doc-forge out of 写作08, 写作09, and the LaTeX compile loop. For 写作02, keep the edit log in the Skill itself.
