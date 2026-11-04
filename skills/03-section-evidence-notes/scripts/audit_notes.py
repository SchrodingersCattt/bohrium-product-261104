#!/usr/bin/env python3
"""Section-aligned notes: quotes must be substrings, and the five fields must be present or declined."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harbor import base_result, case_id_of, load_json, write_json

FIELDS = ("question", "data", "method", "finding", "limitation")
HEAD_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
NUM_RE = re.compile(r"^(\d+(?:\.\d+)*)[\.\s]+(\S.{0,120})$")


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


def split_sections(text: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        heading = HEAD_RE.match(line) or NUM_RE.match(line.strip())
        if heading:
            if current:
                sections.append(current)
            if line.lstrip().startswith("#"):
                marks, title = heading.group(1), heading.group(2).strip()
                level = len(marks)
            else:
                number, title = heading.group(1), heading.group(2).strip()
                title = f"{number} {title}"
                level = number.count(".") + 1
            current = {
                "section_id": f"sec{len(sections) + 1}",
                "title": title,
                "level": level,
                "lines": [],
            }
            continue
        if current is None:
            current = {"section_id": "sec0", "title": "(preamble)", "level": 0, "lines": []}
        current["lines"].append(line)
    if current:
        sections.append(current)
    cleaned = []
    for section in sections:
        body = "\n".join(section.pop("lines")).strip()
        if not body and section["title"] == "(preamble)":
            continue
        section["text"] = body
        cleaned.append(section)
    return cleaned


def read_text(case: dict[str, Any], roots: list[Path]) -> tuple[str, str]:
    materials = case.get("materials") if isinstance(case.get("materials"), dict) else {}
    key = materials.get("source") or case.get("source")
    if case.get("text") and not key:
        return str(case["text"]), "inline"
    path = locate(str(key), roots) if key else None
    if path is None:
        raise FileNotFoundError("materials.source is missing")
    return path.read_text(encoding="utf-8"), str(path)


def audit(sections: list[dict[str, Any]], cards: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_id = {section["section_id"]: section for section in sections}
    by_title = {squash(section["title"]).casefold(): section for section in sections}
    issues = []
    seen_quotes: dict[tuple[str, str], str] = {}
    for card in cards:
        quote = str(card.get("evidence_quote") or "")
        section = by_id.get(card.get("section_id"))
        if section is None and card.get("section_title"):
            section = by_title.get(squash(str(card["section_title"])).casefold())
            if section:
                card["section_id"] = section["section_id"]
        if section is None:
            issues.append({"card_id": card.get("card_id"), "reason": "unknown section"})
            continue
        if not quote or squash(quote) not in squash(section["text"]):
            issues.append({"card_id": card.get("card_id"), "reason": "evidence_quote is not in that section"})
        field = card.get("field")
        if field not in FIELDS:
            issues.append({"card_id": card.get("card_id"), "reason": f"field must be one of {FIELDS}"})
        key = (str(field), squash(quote).casefold())
        if key in seen_quotes:
            issues.append({"card_id": card.get("card_id"), "reason": f"duplicate of {seen_quotes[key]}"})
        else:
            seen_quotes[key] = str(card.get("card_id"))
    return cards, issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit section-aligned notes")
    parser.add_argument("--case", required=True)
    parser.add_argument("--input-root", default="")
    parser.add_argument("--notes", default="")
    parser.add_argument("--work", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    case_path = Path(args.case)
    case = load_json(case_path)
    roots = [case_path.parent, Path("/input")]
    if args.input_root:
        roots.append(Path(args.input_root))
    try:
        text, origin = read_text(case, roots)
    except FileNotFoundError as exc:
        result = base_result(case_id_of(case), "refused", str(exc))
        result.update({"paper": {}, "sections": [], "cards": [], "knowledge_points": []})
        result["limits"] = [str(exc)]
        write_json(Path(args.output), result)
        return 0
    sections = split_sections(text)
    materials = case.get("materials") if isinstance(case.get("materials"), dict) else {}
    notes_path = Path(args.notes) if args.notes else None
    if notes_path is None:
        found = locate(str(materials.get("notes") or "notes.json"), [Path(args.work), *roots])
        notes_path = found
    notes = load_json(notes_path) if notes_path and notes_path.exists() else {}
    cards = list(notes.get("cards") or [])
    cards, issues = audit(sections, cards)
    present = {card.get("field") for card in cards if not any(issue.get("card_id") == card.get("card_id") for issue in issues)}
    gaps = []
    for field in FIELDS:
        if field not in present:
            gaps.append({"field": field, "reason": "no card with an in-section quote"})
    points = []
    for card in cards:
        if any(issue.get("card_id") == card.get("card_id") for issue in issues):
            continue
        points.append(
            {
                "point_id": card.get("card_id"),
                "field": card.get("field"),
                "text": card.get("text") or "",
                "section_id": card.get("section_id"),
                "evidence_quote": card.get("evidence_quote"),
            }
        )
    if notes_path is None or not notes_path.exists():
        status, reason = "partial", "sections are cut; notes.json is still required"
    elif issues or gaps:
        status, reason = "partial", "some cards are unanchored or a required field is missing"
    else:
        status, reason = "success", "cards follow the paper's own sections and each quote is a substring"
    result = base_result(case_id_of(case), status, reason)
    public_sections = [
        {
            "section_id": section["section_id"],
            "title": section["title"],
            "level": section["level"],
            "text": section["text"],
        }
        for section in sections
    ]
    result.update(
        {
            "paper": {"path": origin, "n_sections": len(public_sections)},
            "sections": public_sections,
            "cards": cards,
            "knowledge_points": points,
            "field_gaps": gaps,
        }
    )
    result["sources"] = [
        {
            "source_id": section["section_id"],
            "path": origin,
            "locator": section["title"],
            "quote": section["text"][:240],
        }
        for section in public_sections
    ]
    for issue in issues:
        result["uncertainty"].append({"item": str(issue.get("card_id")), "reason": issue["reason"], "needs_human": True})
    for gap in gaps:
        result["uncertainty"].append({"item": gap["field"], "reason": gap["reason"], "needs_human": True})
    if status != "success":
        result["limits"] = [reason]
    result["change_records"].append(
        {
            "id": "notes-1",
            "action": "bind",
            "before": "free summary",
            "after": "section ids plus substring quotes",
            "reason": "a fluent summary can cite the wrong section",
        }
    )
    Path(args.work).mkdir(parents=True, exist_ok=True)
    write_json(Path(args.work) / "sections.json", public_sections)
    write_json(Path(args.output), result)
    write_json(Path(args.work) / "result.json", result)
    print(f"status={status} sections={len(public_sections)} issues={len(issues)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
