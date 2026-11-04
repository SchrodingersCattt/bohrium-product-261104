#!/usr/bin/env python3
"""Number citations with doc-forge and merge duplicate bibliography records."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from docforge_bibliography import CitationResolver, format_entry, load
from gbt7714 import format_gbt, norm_doi
from harbor import base_result, case_id_of, load_json, write_json

CITE_RE = re.compile(r"\\cite[a-zA-Z*]*\{([^}]+)\}|\[@([A-Za-z0-9_:\-]+)\]")
TYPE_RE = re.compile(r"@(?P<type>\w+)\s*\{\s*(?P<key>[^,\s]+)", re.IGNORECASE)


def locate(raw: str, roots: list[Path]) -> Path | None:
    path = Path(raw)
    if path.is_absolute() and path.exists():
        return path
    for root in roots:
        found = root / raw
        if found.exists():
            return found
    return None


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.casefold()))


def jaccard(left: str, right: str) -> float:
    a, b = tokens(left), tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def last_names(author: str) -> set[str]:
    found = set()
    for person in re.split(r"\s+and\s+", author):
        parts = re.sub(r"[^A-Za-z\-\s]", " ", person).split()
        if parts:
            found.add(parts[-1].casefold())
    return found


def entry_types(path: Path) -> dict[str, str]:
    if path.suffix.lower() not in {".bib", ".bibtex"}:
        return {}
    return {match.group("key"): match.group("type").lower() for match in TYPE_RE.finditer(path.read_text(encoding="utf-8"))}


def cite_keys(text: str) -> list[str]:
    keys = []
    for match in CITE_RE.finditer(text):
        blob = match.group(1) or match.group(2) or ""
        for key in re.split(r"\s*[,;]\s*", blob):
            key = key.strip()
            if key:
                keys.append(key)
    return keys


def prefer(left_key: str, left: Any, right_key: str, right: Any) -> str:
    def score(key: str, entry: Any) -> tuple[int, int]:
        venue = str(entry.get("journal") or entry.get("booktitle") or "").casefold()
        value = 0
        if str(entry.get("pages") or "").strip():
            value += 2
        if venue and "arxiv" not in venue:
            value += 2
        if norm_doi(entry.get("doi")):
            value += 1
        return value, -len(key)

    return left_key if score(left_key, left) >= score(right_key, right) else right_key


def cluster(entries: dict[str, Any]) -> tuple[dict[str, str], list[dict[str, Any]], list[dict[str, Any]]]:
    keys = list(entries)
    parent = {key: key for key in keys}

    def find(key: str) -> str:
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    merges = []
    conflicts = []
    for index, left_key in enumerate(keys):
        for right_key in keys[index + 1 :]:
            left, right = entries[left_key], entries[right_key]
            doi_left, doi_right = norm_doi(left.get("doi")), norm_doi(right.get("doi"))
            title_score = jaccard(str(left.get("title") or ""), str(right.get("title") or ""))
            names_overlap = bool(last_names(str(left.get("author") or left.get("authors") or "")) & last_names(str(right.get("author") or right.get("authors") or "")))
            if doi_left and doi_left == doi_right:
                root_left, root_right = find(left_key), find(right_key)
                if root_left != root_right:
                    kept = prefer(root_left, entries[root_left], root_right, entries[root_right])
                    other = root_right if kept == root_left else root_left
                    parent[other] = kept
                    merges.append({"kept": kept, "merged": other, "reason": f"same DOI {doi_left}"})
                continue
            if doi_left and doi_right and doi_left != doi_right and title_score >= 0.92 and names_overlap:
                conflicts.append(
                    {
                        "left": left_key,
                        "right": right_key,
                        "reason": "titles and authors overlap but DOIs differ; not merged",
                    }
                )
                continue
            years = {str(left.get("year") or ""), str(right.get("year") or "")}
            years.discard("")
            year_ok = len(years) <= 1 or (
                len(years) == 2
                and all(item.isdigit() for item in years)
                and abs(int(min(years)) - int(max(years))) <= 2
            )
            if not doi_left and not doi_right and title_score >= 0.92 and names_overlap and year_ok:
                root_left, root_right = find(left_key), find(right_key)
                if root_left != root_right:
                    kept = prefer(root_left, entries[root_left], root_right, entries[root_right])
                    other = root_right if kept == root_left else root_left
                    parent[other] = kept
                    merges.append({"kept": kept, "merged": other, "reason": "title and author overlap; no conflicting DOI"})
    redirect = {key: find(key) for key in keys}
    # Collapse merge records onto final roots.
    final = []
    seen = set()
    for key, root in redirect.items():
        if key != root and (key, root) not in seen:
            seen.add((key, root))
            final.append({"kept": root, "merged": key, "reason": next((item["reason"] for item in merges if item["merged"] == key or item["kept"] in {key, root}), "clustered")})
    return redirect, final, conflicts


def compress(labels: list[int]) -> str:
    numbers = sorted(set(labels))
    if not numbers:
        return ""
    groups = [[numbers[0]]]
    for number in numbers[1:]:
        if number == groups[-1][-1] + 1:
            groups[-1].append(number)
        else:
            groups.append([number])
    parts: list[str] = []
    for group in groups:
        if len(group) >= 3:
            parts.append(f"{group[0]}-{group[-1]}")
        else:
            parts.extend(str(item) for item in group)
    return "[" + ",".join(parts) + "]"


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve and renumber citations")
    parser.add_argument("--case", required=True)
    parser.add_argument("--input-root", default="")
    parser.add_argument("--work", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    case_path = Path(args.case)
    case = load_json(case_path)
    roots = [case_path.parent, Path("/input")]
    if args.input_root:
        roots.append(Path(args.input_root))
    materials = case.get("materials") if isinstance(case.get("materials"), dict) else {}
    bib_path = locate(str(materials.get("bibliography") or "refs.bib"), roots)
    text_path = locate(str(materials.get("manuscript") or "manuscript.tex"), roots)
    if bib_path is None or text_path is None:
        result = base_result(case_id_of(case), "refused", "bibliography and manuscript are required")
        result.update(empty())
        result["limits"] = ["missing bibliography or manuscript"]
        write_json(Path(args.output), result)
        return 0
    entries = load(bib_path)
    types = entry_types(bib_path)
    for key, entry in entries.items():
        if entry.entry_type and entry.entry_type != "misc":
            types.setdefault(key, entry.entry_type)
    redirect, merges, conflicts = cluster(entries)
    manuscript = text_path.read_text(encoding="utf-8")
    raw_keys = cite_keys(manuscript)
    unknown = []
    ordered = []
    for key in raw_keys:
        if key not in redirect:
            unknown.append(key)
            continue
        canon = redirect[key]
        ordered.append(canon)
    policy = str(case.get("numbering") or materials.get("numbering") or "first-citation")
    if policy not in {"first-citation", "source-order"}:
        policy = "first-citation"
    known_entries = {key: value for key, value in entries.items() if key == redirect[key]}
    resolver = CitationResolver(known_entries, strict=True)
    plan_keys = list(dict.fromkeys(ordered))
    if plan_keys:
        number_order, mapping = resolver.plan(plan_keys, numbering=policy)  # type: ignore[arg-type]
    else:
        number_order, mapping = (), {}
    key_to_number = {key: int(mapping[key]) for key in number_order}
    references = []
    for key in number_order:
        entry = known_entries[key]
        kind = types.get(key, entry.entry_type or "misc")
        references.append(
            {
                "number": key_to_number[key],
                "key": key,
                "plain": format_entry(entry, profile="plain"),
                "gbt7714_simplified": format_gbt(entry, kind),
                "entry_type": kind,
            }
        )
    claims_path = locate(str(materials.get("claims") or "claims.json"), [Path(args.work), *roots])
    claim_checks = []
    if claims_path:
        for claim in load_json(claims_path):
            missing = [key for key in claim.get("cite_keys") or [] if redirect.get(key, key) not in key_to_number and key not in entries]
            unresolved = [key for key in claim.get("cite_keys") or [] if key in unknown or redirect.get(key, key) not in known_entries]
            claim_checks.append(
                {
                    "sentence": claim.get("sentence") or "",
                    "cite_keys": claim.get("cite_keys") or [],
                    "claim": claim.get("claim") or "",
                    "unresolved_keys": sorted(set(missing + unresolved)),
                }
            )
    status = "success"
    reason = "known keys were numbered; duplicate DOIs collapsed to one entry"
    if unknown or any(item["unresolved_keys"] for item in claim_checks) or conflicts:
        status = "partial"
        reason = "numbering finished; unknown keys or DOI conflicts are listed and not guessed"
    if not raw_keys:
        status, reason = "partial", "no citation commands were found"
    result = base_result(case_id_of(case), status, reason)
    result.update(
        {
            "numbering_policy": policy,
            "key_to_number": {key: key_to_number[key] for key in number_order},
            "redirect": {key: root for key, root in redirect.items() if key != root},
            "references": references,
            "duplicates": merges,
            "unknown_keys": sorted(set(unknown)),
            "conflicts": conflicts,
            "claim_checks": claim_checks,
            "rendered_cites": compress([key_to_number[key] for key in ordered if key in key_to_number]),
        }
    )
    result["sources"] = [
        {"source_id": "bibliography", "path": str(bib_path), "locator": "library", "quote": ""},
        {"source_id": "manuscript", "path": str(text_path), "locator": "cite commands", "quote": manuscript[:240]},
    ]
    for key in sorted(set(unknown)):
        result["uncertainty"].append({"item": key, "reason": "citation key is not in the library", "needs_human": True})
    for conflict in conflicts:
        result["uncertainty"].append(
            {"item": f"{conflict['left']}/{conflict['right']}", "reason": conflict["reason"], "needs_human": True}
        )
    if not claims_path:
        result["uncertainty"].append(
            {
                "item": "claim_checks",
                "reason": "no claims file; sentence-to-paper fit was not judged",
                "needs_human": True,
            }
        )
    result["change_records"].append(
        {
            "id": "cite-1",
            "action": "renumber",
            "before": "author keys in citation order",
            "after": result["rendered_cites"],
            "reason": f"{policy} numbering after DOI-aware dedup; unknown keys were not invented",
        }
    )
    for merge in merges:
        result["change_records"].append(
            {
                "id": f"merge-{merge['merged']}",
                "action": "merge",
                "before": merge["merged"],
                "after": merge["kept"],
                "reason": merge["reason"],
            }
        )
    if status != "success":
        result["limits"] = [reason]
    Path(args.work).mkdir(parents=True, exist_ok=True)
    write_json(Path(args.output), result)
    print(f"status={status} refs={len(references)} unknown={len(set(unknown))}")
    return 0


def empty() -> dict[str, Any]:
    return {
        "numbering_policy": "",
        "key_to_number": {},
        "references": [],
        "duplicates": [],
        "unknown_keys": [],
        "conflicts": [],
        "claim_checks": [],
    }


if __name__ == "__main__":
    raise SystemExit(main())
