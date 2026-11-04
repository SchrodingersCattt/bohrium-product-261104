# Usage — citation-bibliography

Challenge id: `product-arena-03-429cc14d`.

## Method

`manage_citations.py` loads the library with doc-forge (`CitationResolver`, `load`, `format_entry`, plain profile). It then:

- redirects keys that share a normalized DOI to the record that has pages and a non-arXiv venue when those fields exist
- merges title-and-author overlaps only when neither record has a DOI
- records a conflict when DOIs differ but title Jaccard is at least 0.92 and a last name overlaps
- numbers the remaining keys with doc-forge's `plan` (`first-citation` or `source-order`)
- emits a simplified numeric line with type tags `[J]`, `[M]`, `[C]`, `[D]`, `[EB/OL]`, or `[Z]`

Citation commands recognized: `\cite{key}`, `\citep{key}`, and `[@key]`.

## Commands

```bash
python3 scripts/manage_citations.py --case /input/case.json --input-root /input \
  --work /app/work --output /app/output/result.json
python3 scripts/run_example.py
```

## Dependencies

Python standard library plus the copied doc-forge modules. No pip install. License: `resources/DOC-FORGE-LICENSE.txt`.

## Limits

- The simplified GB/T-style line does not implement every GB/T 7714 rule (author truncation beyond three names uses `et al`, punctuation is ASCII).
- Claim-to-paper truth is only a key check. Without abstracts or full texts, do not grade whether the sentence is fair.
- Numeric body citations such as `[12]` are not remapped unless they are cite keys.
