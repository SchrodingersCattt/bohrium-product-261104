---
name: literature-kg-align
description: >
  Build a two-paper literature graph whose nodes and edges are quotes from
  paragraph ids, merging aliases only when long forms agree and attributes
  do not conflict. Use for literature knowledge graphs, entity alignment, or
  evidence-bound queries.
---

# Literature graph with conservative merges

Challenge: `product-arena-10-760d1a0b` (阅读15｜文献知识图谱构建).

Sharp sub-problem: two real papers in one graph, with executable queries. Co-occurrence is not an edge. A shared method name is not a shared measurement. Paragraph ids from the organizer are the locators. They are not PDF page numbers. Do not invent page 1.

## Inputs the case may use

- `corpus-manifest.json`: per document `source_id`, DOI, title, authors, license, hash.
- `primary-material.json` and `secondary-material.json`: `source_id` plus `paragraphs[]` with `paragraph_id`, `section`, `text`.
- `material.json` may be an index. Read the two material files. Do not treat two serializations of one paper as two papers.
- The primary DOI, title, and authors stay on the primary document.

## Procedure

1. Read both materials and the manifest. Record each document's DOI separately.
2. Write `candidates.json`. Every node needs `local_id`, `source_id`, `paragraph_id`, `surface`, `type`, `evidence`, and optional `aliases` and `attributes`. The surface and the evidence quote must occur in that paragraph. Types you may use: `method`, `dataset`, `metric`, `material`, `task`, `researcher`, `conclusion`, or `untyped` if you truly cannot tell. Every edge needs `source_local`, `target_local`, `relation`, `source_id`, `paragraph_id`, `evidence`. Allowed relations are listed in `scripts/build_graph.py` (`uses`, `evaluated_on`, `trained_on`, `reports`, `outperforms`, `underperforms`, `compares`, `supports`, `contradicts`, `part_of`, `implemented_with`, `measures`, `proposes`).
3. Write at least three queries in `queries.json`:
   - `{"query_id","type":"find_surface","surface"}`
   - `{"query_id","type":"outgoing","surface"}`
   - `{"query_id","type":"conflicts"}`
4. Run:

```bash
python3 /skills/weekly-skill/scripts/build_graph.py \
  --case /input/case.json --input-root /input \
  --candidates /app/work/candidates.json \
  --queries /app/work/queries.json \
  --work /app/work --output /app/output/result.json
```

5. Read `rejected`, `merges`, and `conflicts`. Do not force a rejected surface back in. Do not merge two metric nodes whose `value` attributes differ. Validate with `scripts/validate_result.py`.

The script also harvests `Long Form (ABBR)` pairs by itself. A candidate with the same alias and a long-form token overlap of at least 0.8 can merge across papers. Conflicting attribute values block the merge and become a conflict. Same-paper abbreviations merge. Generic words do not merge just because both papers use them.

## result.json

Envelope plus `graph.nodes`, `graph.edges`, `merges`, `conflicts`, `rejected`, `queries` (executed, with hits and evidence), `documents` (DOI kept per source), `position_note`.

Each node and edge evidence item has `source_id`, `paragraph_id`, and `quote`.

`status` is `partial` if fewer than three queries ran or the candidate file is missing. `success` means the graph was built from grounded candidates and the queries ran. Rejected junk does not by itself fail the run; it is listed under `uncertainty`.

## Failure rules

- Surface not in the paragraph: rejected. Do not keep it.
- Edge whose endpoints were rejected: rejected.
- Do not copy the primary DOI onto the secondary paper.
- Do not treat JSON and Markdown of the same paper as cross-paper evidence.
- A missing PDF page number stays null. Say the locator is a paragraph id.

## Example

`examples/minimal/` has two fictional notes. WideNet merges. The two accuracy values do not. ImageNet is rejected. CNN stays a different node. Not an official case.
