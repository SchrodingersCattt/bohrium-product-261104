#!/usr/bin/env python3
"""Split claims into spans, then audit assertion records against those spans."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harbor import base_result, case_id_of, load_json, write_json

SPLIT_RE = re.compile(r"\s*;\s*|\s+\b(?:while|whereas)\b\s+", re.IGNORECASE)
SENT_RE = re.compile(r"(?<=[.!?])\s+")
PROVENANCE_KEYS = ("source_id", "title", "authors", "year")


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


def spans_of(text: str) -> list[dict[str, str]]:
    spans = []
    for sentence in SENT_RE.split(text.strip()):
        if not sentence.strip():
            continue
        for clause in SPLIT_RE.split(sentence):
            clause = clause.strip()
            if clause:
                spans.append({"span_id": f"sp{len(spans) + 1}", "text": clause})
    return spans


def read_source(case: dict[str, Any], roots: list[Path]) -> tuple[str, str]:
    materials = case.get("materials") if isinstance(case.get("materials"), dict) else {}
    if case.get("text") and not materials.get("source"):
        return str(case["text"]), "inline"
    path = locate(str(materials.get("source") or case.get("source") or ""), roots)
    if path is None:
        raise FileNotFoundError("materials.source is missing")
    payload_text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        payload = json_loads(payload_text)
        return str(payload.get("text") or ""), str(path)
    return payload_text, str(path)


def json_loads(text: str) -> dict[str, Any]:
    import json

    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("source json must be an object")
    return value


def provenance_of(case: dict[str, Any]) -> dict[str, Any]:
    materials = case.get("materials") if isinstance(case.get("materials"), dict) else {}
    raw = case.get("paper_provenance") or materials.get("paper_provenance") or {}
    return dict(raw) if isinstance(raw, dict) else {}


def relation_hit(text: str, relations: set[str]) -> tuple[str, str] | None:
    folded = squash(text).casefold()
    hits = []
    for relation in relations:
        phrase = relation.replace("_", " ")
        if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", folded):
            hits.append((len(phrase), relation, phrase))
    if not hits:
        return None
    hits.sort(reverse=True)
    return hits[0][1], hits[0][2]


def draft_payload(spans: list[dict[str, str]], relations: set[str], case: dict[str, Any]) -> dict[str, Any]:
    """Account for every span from the source when assertions.json was not written."""
    provenance = provenance_of(case)
    complete = all(provenance.get(key) for key in PROVENANCE_KEYS)
    assertions = []
    rejected = []
    if not complete:
        for span in spans:
            rejected.append(
                {
                    "span_id": span["span_id"],
                    "reason": "paper provenance is not in the case; span left unasserted",
                }
            )
        return {"paper_provenance": provenance, "assertions": assertions, "rejected_spans": rejected}
    for span in spans:
        hit = relation_hit(span["text"], relations)
        if hit is None:
            rejected.append({"span_id": span["span_id"], "reason": "span is not a controlled claim"})
            continue
        relation, phrase = hit
        folded = squash(span["text"])
        match = re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", folded, re.IGNORECASE)
        before = squash(folded[: match.start()]) if match else ""
        after = squash(folded[match.end() :]) if match else ""
        before = before.rstrip(" ,:;")
        after = after.rstrip(" .")
        if not before or before.casefold() not in squash(span["text"]).casefold():
            rejected.append({"span_id": span["span_id"], "reason": "no subject before the relation"})
            continue
        assertions.append(
            {
                "assertion_id": f"a-{span['span_id']}",
                "span_id": span["span_id"],
                "subject": before,
                "relation": relation,
                "object": after,
                "conditions": [],
                "assertion_text": squash(span["text"]).rstrip(".") + ".",
                "evidence_quote": span["text"],
                "evidence_kind": "direct",
                "confidence": 0.5,
                "confidence_basis": "The relation word and subject are inside this span.",
                "provenance": {key: provenance.get(key) for key in PROVENANCE_KEYS},
            }
        )
    return {"paper_provenance": provenance, "assertions": assertions, "rejected_spans": rejected}


def audit_items(
    spans: list[dict[str, str]],
    assertions: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
    relations: set[str],
) -> list[dict[str, Any]]:
    by_span = {span["span_id"]: span["text"] for span in spans}
    issues = []
    covered = set()
    for item in rejected:
        span_id = item.get("span_id")
        if span_id not in by_span:
            issues.append({"item": span_id, "check": "unknown_span", "detail": "rejected span id is not in the source"})
        elif not item.get("reason"):
            issues.append({"item": span_id, "check": "missing_reason", "detail": "a rejected span needs a reason"})
        else:
            covered.add(span_id)
    for assertion in assertions:
        span_id = assertion.get("span_id")
        quote = str(assertion.get("evidence_quote") or "")
        if span_id not in by_span:
            issues.append({"item": assertion.get("assertion_id"), "check": "unknown_span", "detail": span_id})
        else:
            covered.add(span_id)
            if squash(quote) not in squash(by_span[span_id]):
                issues.append(
                    {
                        "item": assertion.get("assertion_id"),
                        "check": "evidence_not_in_span",
                        "detail": "quote must be a substring of its span",
                    }
                )
        relation = str(assertion.get("relation") or "")
        if relation not in relations and assertion.get("relation_status") != "proposed":
            issues.append(
                {
                    "item": assertion.get("assertion_id"),
                    "check": "relation_not_controlled",
                    "detail": relation or "(empty)",
                }
            )
        subject = squash(str(assertion.get("subject") or ""))
        if subject and subject.casefold() not in squash(quote).casefold():
            issues.append(
                {
                    "item": assertion.get("assertion_id"),
                    "check": "subject_not_in_evidence",
                    "detail": subject,
                }
            )
        if ";" in str(assertion.get("assertion_text") or "") or isinstance(assertion.get("span_ids"), list):
            issues.append(
                {
                    "item": assertion.get("assertion_id"),
                    "check": "too_wide",
                    "detail": "one assertion may cover one span",
                }
            )
        provenance = assertion.get("provenance") if isinstance(assertion.get("provenance"), dict) else {}
        missing = [key for key in PROVENANCE_KEYS if not provenance.get(key)]
        if missing:
            issues.append(
                {
                    "item": assertion.get("assertion_id"),
                    "check": "provenance_missing",
                    "detail": ",".join(missing),
                }
            )
        if assertion.get("evidence_kind") not in {"direct", "inference"}:
            issues.append(
                {
                    "item": assertion.get("assertion_id"),
                    "check": "evidence_kind",
                    "detail": "use direct or inference",
                }
            )
    for span in spans:
        if span["span_id"] not in covered:
            issues.append({"item": span["span_id"], "check": "span_not_accounted", "detail": span["text"][:120]})
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit nanopublication assertions")
    parser.add_argument("--case", required=True)
    parser.add_argument("--input-root", default="")
    parser.add_argument("--assertions", default="")
    parser.add_argument("--work", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    case_path = Path(args.case)
    case = load_json(case_path)
    roots = [case_path.parent, Path("/input")]
    if args.input_root:
        roots.append(Path(args.input_root))
    skill_root = Path(__file__).resolve().parents[1]
    relations = set(load_json(skill_root / "resources" / "relations.json")["relations"])
    try:
        text, origin = read_source(case, roots)
    except FileNotFoundError as exc:
        result = base_result(case_id_of(case), "refused", str(exc))
        result.update({"provenance": {}, "assertions": [], "quality_checks": [], "spans": []})
        result["limits"] = [str(exc)]
        write_json(Path(args.output), result)
        return 0
    spans = spans_of(text)
    materials = case.get("materials") if isinstance(case.get("materials"), dict) else {}
    path = Path(args.assertions) if args.assertions else locate(str(materials.get("assertions") or "assertions.json"), [Path(args.work), *roots])
    payload = load_json(path) if path and path.exists() else draft_payload(spans, relations, case)
    assertions = list(payload.get("assertions") or [])
    rejected = list(payload.get("rejected_spans") or [])
    issues = audit_items(spans, assertions, rejected, relations)
    hard = [issue for issue in issues if issue["check"] != "relation_not_controlled"]
    proposed = [issue for issue in issues if issue["check"] == "relation_not_controlled"]
    if hard:
        status, reason = "partial", "at least one assertion failed a structural check"
    elif not assertions and spans:
        status, reason = "partial", "no assertion was accepted"
    else:
        status, reason = "success", "each span is one assertion or an explicit rejection, with a quote inside that span"
    result = base_result(case_id_of(case), status, reason)
    result.update(
        {
            "provenance": payload.get("paper_provenance") or {},
            "spans": spans,
            "assertions": assertions,
            "rejected_spans": rejected,
            "quality_checks": issues,
        }
    )
    result["sources"] = [
        {"source_id": span["span_id"], "path": origin, "locator": span["span_id"], "quote": span["text"]}
        for span in spans
    ]
    for issue in issues:
        result["uncertainty"].append(
            {"item": str(issue.get("item")), "reason": f"{issue['check']}: {issue['detail']}", "needs_human": True}
        )
    if proposed and status == "success":
        result["status"] = "partial"
        result["status_reason"] = "structure passed; an unlisted relation is only proposed"
    if result["status"] != "success":
        result["limits"] = [result["status_reason"]]
    result["change_records"].append(
        {
            "id": "nano-1",
            "action": "split",
            "before": "paragraph-sized claim",
            "after": "one span id per assertion, quote contained in that span",
            "reason": "a paragraph often joins two claims that do not share evidence",
        }
    )
    Path(args.work).mkdir(parents=True, exist_ok=True)
    write_json(Path(args.work) / "spans.json", spans)
    write_json(Path(args.output), result)
    print(f"status={result['status']} spans={len(spans)} issues={len(issues)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
