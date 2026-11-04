#!/usr/bin/env python3
"""Apply sentence edits only when numbers, units, citations, and hedge strength stay put."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harbor import base_result, case_id_of, load_json, write_json

SENT_RE = re.compile(r"(?<=[.!?])\s+")
NUM_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?")
UNIT_RE = re.compile(
    r"(?<![\w.])\d+(?:\.\d+)?\s*(?:mg/L|mm|cm|nm|mg|kg|mL|ml|°C|%|ms|Hz)\b",
    re.IGNORECASE,
)
CITE_RE = re.compile(r"\[[0-9]+(?:\s*[,;\-–]\s*[0-9]+)*\]|\\cite[a-zA-Z*]*\{[^}]+\}|\([A-Z][A-Za-z'\-]+,\s*\d{4}\)")
FIG_RE = re.compile(r"\b(?:Figure|Fig\.|Table|Tab\.)\s*~?\s*\d+|\b(?:图|表)\s*\d+", re.IGNORECASE)
WEAK = ("may", "might", "could", "suggests", "suggest", "appears", "appear", "possibly", "potentially", "likely", "seems")
STRONG = ("prove", "proves", "proven", "demonstrate", "demonstrates", "establish", "establishes", "confirm", "confirms", "clearly", "definitely", "certainly")
EDIT_TYPES = {"grammar", "punctuation", "terminology", "register", "clarity", "structure", "unchanged"}


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def sentences(text: str) -> list[dict[str, str]]:
    parts = [squash(part) for part in SENT_RE.split(text.strip()) if squash(part)]
    return [{"sentence_id": f"s{index}", "text": part} for index, part in enumerate(parts, start=1)]


def bag(pattern: re.Pattern[str], text: str) -> list[str]:
    return sorted(match.group(0).replace(" ", "").replace("~", "") for match in pattern.finditer(text))


def words(text: str, lexicon: tuple[str, ...]) -> set[str]:
    found = set()
    for token in lexicon:
        if re.search(rf"(?i)(?<!\w){re.escape(token)}(?!\w)", text):
            found.add(token.lower())
    return found


def locate(raw: str, roots: list[Path]) -> Path | None:
    path = Path(raw)
    if path.is_absolute() and path.exists():
        return path
    for root in roots:
        found = root / raw
        if found.exists():
            return found
    return None


def preservation_issues(original: str, revised: str) -> list[str]:
    issues = []
    if bag(NUM_RE, original) != bag(NUM_RE, revised):
        issues.append(f"numbers {bag(NUM_RE, original)} vs {bag(NUM_RE, revised)}")
    if [item.lower() for item in bag(UNIT_RE, original)] != [item.lower() for item in bag(UNIT_RE, revised)]:
        issues.append("units changed")
    if bag(CITE_RE, original) != bag(CITE_RE, revised):
        issues.append("citations changed")
    if [item.lower() for item in bag(FIG_RE, original)] != [item.lower() for item in bag(FIG_RE, revised)]:
        issues.append("figure or table references changed")
    return issues


def strength_shift(original: str, revised: str) -> str:
    weak_before, strong_before = words(original, WEAK), words(original, STRONG)
    weak_after, strong_after = words(revised, WEAK), words(revised, STRONG)
    if weak_before and (weak_before - weak_after) and (strong_after - strong_before):
        return "hedge strengthened"
    if re.search(r"(?i)\bcorrelat", original) and re.search(r"(?i)\bcaus", revised) and not re.search(r"(?i)\bcaus", original):
        return "correlation rewritten as causation"
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit academic sentence edits")
    parser.add_argument("--case", required=True)
    parser.add_argument("--input-root", default="")
    parser.add_argument("--edits", default="")
    parser.add_argument("--work", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    case_path = Path(args.case)
    case = load_json(case_path)
    roots = [case_path.parent, Path("/input")]
    if args.input_root:
        roots.append(Path(args.input_root))
    materials = case.get("materials") if isinstance(case.get("materials"), dict) else {}
    source_path = locate(str(materials.get("source") or "source.txt"), roots)
    if source_path is None and not case.get("text"):
        result = base_result(case_id_of(case), "refused", "source text is missing")
        result.update({"revised_text": "", "edits": [], "preservation": []})
        result["limits"] = ["missing source"]
        write_json(Path(args.output), result)
        return 0
    source = case["text"] if case.get("text") and source_path is None else source_path.read_text(encoding="utf-8")
    rows = sentences(source)
    by_id = {row["sentence_id"]: row["text"] for row in rows}
    edits_path = Path(args.edits) if args.edits else locate(str(materials.get("edits") or "edits.json"), [Path(args.work), *roots])
    proposed = load_json(edits_path) if edits_path and edits_path.exists() else {}
    proposals = {item.get("sentence_id"): item for item in proposed.get("edits") or []}
    applied = []
    revised_parts = []
    issues = []
    for row in rows:
        original = row["text"]
        proposal = proposals.get(row["sentence_id"])
        if proposal is None:
            revised_parts.append(original)
            continue
        if squash(str(proposal.get("original") or "")) != original:
            issues.append({"sentence_id": row["sentence_id"], "reason": "original does not match the source sentence"})
            revised_parts.append(original)
            continue
        revised = squash(str(proposal.get("revised") or "")) or original
        edit_type = str(proposal.get("edit_type") or "")
        reason = str(proposal.get("reason") or "")
        problems = preservation_issues(original, revised)
        shift = strength_shift(original, revised)
        if problems or shift or edit_type not in EDIT_TYPES or not reason:
            detail = "; ".join(problems + ([shift] if shift else []) + ([] if edit_type in EDIT_TYPES else ["bad edit_type"]) + ([] if reason else ["missing reason"]))
            issues.append({"sentence_id": row["sentence_id"], "reason": detail or "rejected"})
            revised_parts.append(original)
            applied.append(
                {
                    "sentence_id": row["sentence_id"],
                    "original": original,
                    "revised": original,
                    "edit_type": "rejected",
                    "reason": detail,
                    "applied": False,
                }
            )
            continue
        revised_parts.append(revised)
        applied.append(
            {
                "sentence_id": row["sentence_id"],
                "original": original,
                "revised": revised,
                "edit_type": edit_type,
                "reason": reason,
                "applied": revised != original,
            }
        )
    if edits_path is None or not edits_path.exists():
        status, reason = "partial", "sentences are split; edits.json is still required"
    elif issues:
        status, reason = "partial", "some edits were reverted because they changed facts or strength"
    else:
        status, reason = "success", "applied edits keep numbers, units, citations, and hedge strength"
    result = base_result(case_id_of(case), status, reason)
    result.update(
        {
            "revised_text": " ".join(revised_parts),
            "edits": applied,
            "preservation": [
                {"sentence_id": row["sentence_id"], "numbers": bag(NUM_RE, row["text"]), "citations": bag(CITE_RE, row["text"])}
                for row in rows
            ],
            "sentences": rows,
        }
    )
    result["sources"] = [
        {"source_id": row["sentence_id"], "path": str(source_path or "inline"), "locator": row["sentence_id"], "quote": row["text"]}
        for row in rows
    ]
    for issue in issues:
        result["uncertainty"].append({"item": issue["sentence_id"], "reason": issue["reason"], "needs_human": True})
        result["change_records"].append(
            {
                "id": f"reject-{issue['sentence_id']}",
                "action": "revert",
                "before": issue["reason"],
                "after": by_id[issue["sentence_id"]],
                "reason": "edit failed a preservation check",
            }
        )
    for edit in applied:
        if edit.get("applied"):
            result["change_records"].append(
                {
                    "id": f"edit-{edit['sentence_id']}",
                    "action": edit["edit_type"],
                    "before": edit["original"],
                    "after": edit["revised"],
                    "reason": edit["reason"],
                }
            )
    if status != "success":
        result["limits"] = [reason]
    Path(args.work).mkdir(parents=True, exist_ok=True)
    write_json(Path(args.output), result)
    print(f"status={status} edits={len(applied)} reverted={len(issues)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
