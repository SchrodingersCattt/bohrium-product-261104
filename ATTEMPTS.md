# Attempts

Built on 2026-11-04 for period 2. No Playground scores are recorded. Official organizer cases were not run. Each `examples/minimal/` tree is a labeled toy and is not a prepared contest answer.

## What was built

Ten Harbor skills under `skills/`. Each has `SKILL.md` (YAML `name` and `description`), `USAGE.md`, `scripts/`, `resources/output_contract.json`, and `examples/minimal/` with a passing `run_example.py`. Shared envelope checks live in `scripts/harbor.py` and `scripts/validate_result.py`. The model writes prose or candidate records. The scripts reject text, numbers, quotes, or merges that the source does not support.

| Slot | Package | Challenge | Method |
|---|---|---|---|
| 01 | `skills/01-pdf-reading-order` | `product-arena-08-3027d350` | Order PDF lines by left-edge columns. Headers stay out of body flow. Formula spans stay separate. Image-only pages stay undetermined. |
| 02 | `skills/02-literature-term-lock` | `product-arena-01-5a9928c1` | Blank-line segments. Audit number multisets, units, citation surfaces, formulas, and locked glossary targets. |
| 03 | `skills/03-section-evidence-notes` | `product-arena-06-6d8cf72b` | Split on headings. A card counts only when its quote is inside that section. Missing fields stay gaps. |
| 04 | `skills/04-nanopub-assertions` | `product-arena-09-0e8befd4` | Split on sentence boundaries, semicolons, and while/whereas. One span per assertion. Relations come from `resources/relations.json`. Twenty fictional shapes are style examples only. |
| 05 | `skills/05-literature-kg` | `product-arena-10-760d1a0b` | Two paragraph files keep their own DOIs. Alias merge needs long-form overlap and matching attributes. Co-occurrence is not an edge. Queries actually run. Locators are paragraph ids. |
| 06 | `skills/06-academic-polish` | `product-arena-02-7051d92d` | Sentence ledger. Edits that change numbers, units, citations, figure or table numbers, or hedge strength are reverted. |
| 07 | `skills/07-citation-bibliography` | `product-arena-03-429cc14d` | doc-forge bibliography modules at commit `2e93c80e34262afcb9ae4c3db38155e26190852d` (MIT). Same DOI merges. Different DOIs with the same title conflict. Unknown keys are not numbered. Simplified `[J]`/`[M]` lines are not a certified GB/T 7714 renderer. |
| 08 | `skills/08-intro-related-work` | `product-arena-04-4b82ad21` | Comparison cells quote the named paper. Contributions point at inventory evidence ids. Gaps are premises or marked author judgment. |
| 09 | `skills/09-methods-from-config` | `product-arena-05-64faa4a2` | Parameter table from JSON scalars and `key: value` lines. Prose numbers must match. A missing dataset is `not_in_source` and the status stays partial. |
| 10 | `skills/10-latex-compile` | `product-arena-07-865de7e4` | `pdflatex` with log lines mapped to file and line. Local check for undefined or uncited `fig:` and `tab:` labels. No DOCX converter and no doc-forge copy. |

`scripts/run_example.py` passed for all ten packages after the last edit. Toy controls also fail closed: dropped translation numbers, a changed note quote, a too-wide nanopub span, an ungrounded graph surface, a strengthened hedge, an unknown cite key, a quote the cited paper does not contain, a methods number absent from config, and a LaTeX undefined control sequence.

## Submission order

Upload `submissions/01` through `submissions/10` in that order. That matches the period page, which is not the numeric order of the `product-arena-0N` ids.

1. `submissions/01` — document parsing — `product-arena-08-3027d350`
2. `submissions/02` — translation — `product-arena-01-5a9928c1`
3. `submissions/03` — structured notes — `product-arena-06-6d8cf72b`
4. `submissions/04` — nanopublication — `product-arena-09-0e8befd4`
5. `submissions/05` — knowledge graph — `product-arena-10-760d1a0b`
6. `submissions/06` — language polish — `product-arena-02-7051d92d`
7. `submissions/07` — references — `product-arena-03-429cc14d`
8. `submissions/08` — introduction and related work — `product-arena-04-4b82ad21`
9. `submissions/09` — methods and experiments — `product-arena-05-64faa4a2`
10. `submissions/10` — LaTeX compile — `product-arena-07-865de7e4`

## Not done

No git commit and no git push. No secrets file. The full `vendor/doc-forge` tree is not inside any skill. Only the bibliography modules used by slot 07 are copied, with `NOTICE.md` and the MIT license.
