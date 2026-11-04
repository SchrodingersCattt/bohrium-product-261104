# Usage — literature-kg-align

Challenge id: `product-arena-10-760d1a0b`.

## Method

`build_graph.py` loads the manifest and both paragraph files. It harvests capitalized long forms defined as `Name (ABBR)`. It then keeps candidate nodes and edges only when the surface and the evidence quote are in the cited paragraph. Merge rules:

- Same paper and a shared alias: merge.
- Across papers: merge only when an alias is shared and the long-form token Jaccard is at least 0.8, and no shared attribute value differs.
- Same surface with different `value` (or any shared attribute): do not merge; record a conflict.

Queries are executed on that graph. `find_surface` and `outgoing` match the canonical surface and aliases. `conflicts` returns the unmerged pairs.

## Commands

```bash
python3 scripts/build_graph.py --case /input/case.json --input-root /input \
  --work /app/work --output /app/output/result.json
python3 scripts/run_example.py
```

## Limits

- The script does not invent edges from two entities appearing in one paragraph. You must propose the edge with a quote.
- Abbreviation harvest misses lowercase aliases and abbreviations that are never defined in parentheses.
- Types are whatever the candidate file says, or `untyped` for harvested nodes the candidate file did not type.
- Locators are paragraph ids. This package does not contain PDF page numbers.
