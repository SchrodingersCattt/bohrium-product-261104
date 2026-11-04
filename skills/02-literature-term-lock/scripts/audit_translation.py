#!/usr/bin/env python3
"""Check a segment-aligned translation against locked terms, numbers, cites, and formulas."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harbor import base_result, case_id_of, load_json, write_json
from segment_source import build

NUM_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?")


def squash(text: str) -> str:
    swapped = text.replace("（", "(").replace("）", ")").replace("，", ",")
    return re.sub(r"\s+", " ", swapped).strip()


def load_optional(path: Path | None) -> Any:
    if path is None or not path.exists():
        return None
    return load_json(path)


def locate(raw: str, roots: list[Path]) -> Path | None:
    candidate = Path(raw)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    for root in roots:
        found = root / raw
        if found.exists():
            return found
    return None


def contains_term(text: str, term: str) -> bool:
    if re.search(r"[A-Za-z]", term):
        return re.search(rf"(?i)(?<!\w){re.escape(term)}(?!\w)", text) is not None
    return term.casefold() in text.casefold()


def audit(segments: list[dict[str, Any]], glossary: dict[str, Any], translated: dict[str, Any]) -> dict[str, Any]:
    by_id = {item["seg_id"]: item for item in translated.get("segments") or []}
    issues = []
    rows = []
    locked = [entry for entry in glossary.get("entries") or [] if entry.get("locked")]
    unit_map = {str(item["source"]): str(item["target"]) for item in glossary.get("unit_maps") or []}
    for segment in segments:
        target = by_id.get(segment["seg_id"])
        translation = squash(str(target.get("translation") or "")) if target else ""
        row_issues = []
        if target is None or not translation:
            row_issues.append("missing translation")
        source_nums = segment["numbers"]
        target_nums = NUM_RE.findall(translation)
        if sorted(source_nums) != sorted(target_nums):
            row_issues.append(f"numbers {source_nums} vs {target_nums}")
        for cite in segment["citations"]:
            if squash(cite) not in translation and cite not in translation:
                row_issues.append(f"citation missing: {cite}")
        for formula in segment["formulas"]:
            if formula not in (target.get("translation") if target else ""):
                row_issues.append(f"formula missing: {formula}")
        for unit in segment["units"]:
            surface = unit["unit"]
            allowed = {surface, unit_map.get(surface, surface)}
            if not any(token in translation for token in allowed):
                row_issues.append(f"unit missing: {surface}")
        for entry in locked:
            source_term = str(entry.get("source") or "")
            target_term = str(entry.get("target") or "")
            if source_term and contains_term(segment["text"], source_term):
                if not target_term or target_term not in translation:
                    row_issues.append(f"locked term not applied: {source_term} -> {target_term}")
        if row_issues:
            issues.append({"seg_id": segment["seg_id"], "issues": row_issues})
        rows.append(
            {
                "seg_id": segment["seg_id"],
                "source": segment["text"],
                "translation": translation,
                "issues": row_issues,
            }
        )
    extra = sorted(set(by_id) - {segment["seg_id"] for segment in segments})
    for seg_id in extra:
        issues.append({"seg_id": seg_id, "issues": ["translation has no source segment"]})
    return {"rows": rows, "issues": issues, "extra_segment_ids": extra}


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit a locked translation")
    parser.add_argument("--case", required=True)
    parser.add_argument("--input-root", default="")
    parser.add_argument("--segments", default="")
    parser.add_argument("--glossary", default="")
    parser.add_argument("--translation", default="")
    parser.add_argument("--work", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    case_path = Path(args.case)
    case = load_json(case_path)
    roots = [case_path.parent, Path("/input")]
    if args.input_root:
        roots.append(Path(args.input_root))
    agent_roots = [Path(args.work), *roots]
    materials = case.get("materials") if isinstance(case.get("materials"), dict) else {}
    if args.segments:
        prepared = load_json(Path(args.segments))
    else:
        prepared = build(case, roots)
    glossary_path = Path(args.glossary) if args.glossary else locate(str(materials.get("glossary") or "glossary.json"), agent_roots)
    translation_path = Path(args.translation) if args.translation else locate(str(materials.get("translation") or "translation.json"), agent_roots)
    glossary = load_optional(glossary_path) or {"entries": []}
    translated = load_optional(translation_path) or {"segments": []}
    report = audit(prepared["segments"], glossary, translated)
    missing_files = []
    if glossary_path is None or not Path(glossary_path).exists():
        missing_files.append("glossary")
    if translation_path is None or not Path(translation_path).exists():
        missing_files.append("translation")
    if missing_files:
        status, reason = "partial", "segments are ready; " + " and ".join(missing_files) + " still required from the model"
    elif report["issues"]:
        status, reason = "partial", "one or more segments failed the lock checks"
    elif not prepared["segments"]:
        status, reason = "undetermined", "source had no segments"
    else:
        status, reason = "success", "every segment keeps numbers, units, citations, formulas, and locked terms"
    result = base_result(case_id_of(case), status, reason)
    result.update(
        {
            "source_language": translated.get("source_language") or case.get("source_language") or "",
            "target_language": translated.get("target_language") or case.get("target_language") or "",
            "glossary": glossary.get("entries") or [],
            "segments": report["rows"],
            "audit": {"issues": report["issues"], "n_segments": len(prepared["segments"])},
        }
    )
    result["sources"] = [
        {
            "source_id": segment["seg_id"],
            "path": prepared["source_path"],
            "locator": segment["seg_id"],
            "quote": segment["text"][:240],
        }
        for segment in prepared["segments"]
    ]
    for issue in report["issues"]:
        result["uncertainty"].append(
            {"item": issue["seg_id"], "reason": "; ".join(issue["issues"]), "needs_human": True}
        )
    if missing_files:
        result["limits"] = [f"missing {name}" for name in missing_files]
    result["change_records"].append(
        {
            "id": "lock-1",
            "action": "audit",
            "before": "free translation",
            "after": "segment ids with number, unit, citation, formula, and glossary checks",
            "reason": "a fluent paragraph can drop a numeral or rename a locked term",
        }
    )
    write_json(Path(args.output), result)
    write_json(Path(args.work) / "segments.json", prepared)
    write_json(Path(args.work) / "result.json", result)
    print(f"status={status} issues={len(report['issues'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
