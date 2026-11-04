---
name: citation-bibliography
description: >
  Number manuscript citations from a BibTeX or JSON library, merge records
  that share a DOI, and leave unknown keys unresolved. Use for reference
  management, citation renumbering, or bibliography deduplication.
---

# Citation numbering and DOI dedup

Challenge: `product-arena-03-429cc14d` (写作04｜参考文献与引用管理).

Sharp sub-problem: after inserts and deletions, body numbers and the reference list stay in lockstep, duplicate records collapse when the DOI matches, and an unknown key fails closed.

Numbering and plain reference lines come from doc-forge's bibliography package (MIT), copied under `scripts/docforge_bibliography/`. Upstream commit `2e93c80e34262afcb9ae4c3db38155e26190852d`. See `scripts/docforge_bibliography/NOTICE.md`. The `[J]` / `[M]` / `[C]` lines are a simplified profile in `scripts/gbt7714.py`. They are not a certified GB/T 7714-2015 renderer. doc-forge does not provide that profile.

## Procedure

1. Read the manuscript and the `.bib` or JSON library from the case. Do not add a paper that is not in the library.
2. Optional `/app/work/claims.json`, or the path in `materials.claims`: a list of `{sentence, cite_keys, claim}` for cited sentences. Keys that are not in the library are reported, not repaired. A file in `/app/work` is preferred over a file of the same name beside the case.
3. Run:

```bash
python3 /skills/weekly-skill/scripts/manage_citations.py \
  --case /input/case.json --input-root /input \
  --work /app/work --output /app/output/result.json
```

Set `numbering` on the case to `first-citation` (default) or `source-order`.

4. Read `unknown_keys`, `redirect`, `duplicates`, and `conflicts`. Same DOI: one number, alias keys redirect. Two records with the same title and overlapping authors but different DOIs are conflicts, not a merge. Do not delete the conflict by hand inside the script output; leave it for a person.
5. If you still need to decide whether a sentence's claim matches the cited paper, say so in `uncertainty` when the library has no abstract. Do not assert a match you did not read.
6. Validate with `scripts/validate_result.py`.

## result.json

Envelope plus `numbering_policy`, `key_to_number`, `redirect`, `references` (`plain` from doc-forge and `gbt7714_simplified`), `duplicates`, `unknown_keys`, `conflicts`, `claim_checks`, `rendered_cites`.

`status` is `partial` when any cited key is unknown, a DOI conflict exists, or no cite command was found. `success` means every cited key resolved and no DOI conflict was detected. Unknown keys are never dropped into the numbered list.

## Failure rules

- Missing library or manuscript: `refused`.
- Unknown `\cite{key}` or `[@key]`: listed in `unknown_keys`, omitted from `key_to_number`.
- Do not invent a DOI to force a merge.
- Chinese and English titles of the same work are not auto-merged. Flag them yourself only with evidence, as uncertainty, not as a silent redirect.

## Example

`examples/minimal/refs.bib` shares `10.1000/example.1` across a preprint and a published record, and has a second DOI with the same title. `missing` is unknown. Not an official case.
