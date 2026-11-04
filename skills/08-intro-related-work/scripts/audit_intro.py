#!/usr/bin/env python3
"""Check a related-work table: every cell quote is in that paper, every contribution has evidence."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harbor import base_result, case_id_of, load_json, write_json


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def locate(raw: str, roots: list[Path]) -> Path | None:
    path = Path(raw)
    if path.is_absolute() and path.exists():
        return path
    for root in roots:
        found = root / raw
        if found.exists():
            return found
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit an introduction / related-work draft")
    parser.add_argument("--case", required=True)
    parser.add_argument("--input-root", default="")
    parser.add_argument("--draft", default="")
    parser.add_argument("--work", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    case_path = Path(args.case)
    case = load_json(case_path)
    roots = [case_path.parent, Path("/input")]
    if args.input_root:
        roots.append(Path(args.input_root))
    materials = case.get("materials") if isinstance(case.get("materials"), dict) else {}
    library_path = locate(str(materials.get("library") or "library.json"), roots)
    draft_path = Path(args.draft) if args.draft else locate(str(materials.get("draft") or "draft.json"), [Path(args.work), *roots])
    if library_path is None:
        result = base_result(case_id_of(case), "refused", "library.json with prior papers and an evidence inventory is required")
        result.update({"groups": [], "gap": {}, "contributions": [], "prose": "", "citation_coverage": []})
        result["limits"] = ["missing library"]
        write_json(Path(args.output), result)
        return 0
    library = load_json(library_path)
    papers = {item["paper_id"]: item for item in library.get("papers") or []}
    inventory = {item["evidence_id"]: item for item in library.get("inventory") or []}
    draft = load_json(draft_path) if draft_path and draft_path.exists() else {}
    issues = []
    seen: set[str] = set()
    groups = draft.get("groups") or []
    for group in groups:
        if not group.get("axis"):
            issues.append({"item": group.get("group_id"), "reason": "group needs a comparison axis"})
        cells = {cell.get("paper_id"): cell for cell in group.get("cells") or []}
        for paper_id in group.get("paper_ids") or []:
            if paper_id in seen:
                issues.append({"item": paper_id, "reason": "paper appears in more than one group"})
            seen.add(paper_id)
            paper = papers.get(paper_id)
            cell = cells.get(paper_id)
            if paper is None:
                issues.append({"item": paper_id, "reason": "unknown paper id"})
                continue
            if cell is None:
                issues.append({"item": paper_id, "reason": "missing comparison cell"})
                continue
            if cell.get("not_reported"):
                continue
            quote = str(cell.get("quote") or "")
            if not quote or squash(quote) not in squash(str(paper.get("text") or "")):
                issues.append({"item": paper_id, "reason": "cell quote is not in that paper"})
    missing_papers = [paper_id for paper_id in papers if paper_id not in seen]
    for paper_id in missing_papers:
        issues.append({"item": paper_id, "reason": "paper is not in any group"})
    gap = draft.get("gap") or {}
    for premise in gap.get("premise_ids") or []:
        if premise not in papers:
            issues.append({"item": premise, "reason": "gap premise is not a known paper"})
    if gap and not gap.get("premise_ids") and not gap.get("author_judgment"):
        issues.append({"item": "gap", "reason": "gap needs premises or an author_judgment flag"})
    contributions = draft.get("contributions") or []
    for item in contributions:
        evidence_ids = item.get("evidence_ids") or []
        if not evidence_ids:
            issues.append({"item": item.get("text", "")[:40], "reason": "contribution has no evidence id"})
        for evidence_id in evidence_ids:
            if evidence_id not in inventory:
                issues.append({"item": evidence_id, "reason": "contribution evidence is not in the inventory"})
    prose = str(draft.get("prose") or "")
    for cite in re.findall(r"\[@([A-Za-z0-9_:\-]+)\]", prose):
        if cite not in papers and cite not in inventory:
            issues.append({"item": cite, "reason": "prose cite is not a paper or evidence id"})
    coverage = []
    for paper_id, paper in papers.items():
        coverage.append(
            {
                "paper_id": paper_id,
                "grouped": paper_id in seen,
                "title": paper.get("title") or "",
            }
        )
    if draft_path is None or not draft_path.exists():
        status, reason = "partial", "library is loaded; draft.json is still required"
    elif issues:
        status, reason = "partial", "one or more comparison cells or contributions are unbound"
    elif not groups or not contributions:
        status, reason = "partial", "draft needs at least one group and one contribution"
    else:
        status, reason = "success", "groups, gap premises, and contributions point at supplied text"
    result = base_result(case_id_of(case), status, reason)
    result.update(
        {
            "groups": groups,
            "gap": gap,
            "contributions": contributions,
            "prose": prose,
            "citation_coverage": coverage,
        }
    )
    result["sources"] = [
        {
            "source_id": paper_id,
            "path": str(library_path),
            "locator": paper_id,
            "quote": str(paper.get("text") or "")[:240],
        }
        for paper_id, paper in papers.items()
    ]
    for issue in issues:
        result["uncertainty"].append({"item": str(issue["item"]), "reason": issue["reason"], "needs_human": True})
    if status != "success":
        result["limits"] = [reason]
    result["change_records"].append(
        {
            "id": "intro-1",
            "action": "bind",
            "before": "ungrouped related work",
            "after": "one comparison cell per paper, quote copied from that paper",
            "reason": "a chronological list can attribute a limitation to the wrong paper",
        }
    )
    Path(args.work).mkdir(parents=True, exist_ok=True)
    write_json(Path(args.output), result)
    print(f"status={status} issues={len(issues)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
