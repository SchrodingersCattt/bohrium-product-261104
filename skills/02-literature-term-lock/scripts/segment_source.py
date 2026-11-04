#!/usr/bin/env python3
"""Split a source into stable segments and list tokens that translation must keep."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harbor import load_json, write_json

CITE_RES = [
    re.compile(r"\\cite[a-zA-Z*]*\{[^}]+\}"),
    re.compile(r"\[[0-9]+(?:\s*[,;，、\-–]\s*[0-9]+)*\]"),
    re.compile(r"\([A-Z][A-Za-z'\-]+(?:\s+et\s+al\.)?,\s*\d{4}[a-z]?\)"),
]
FORMULA_RE = re.compile(r"\$[^$]+\$|\\\(.+?\\\)")
NUM_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?")
UNIT_RE = re.compile(
    r"(?<![\w.])(\d+(?:\.\d+)?)(?:\s*)(mg/L|µg/mL|ug/mL|mm|cm|nm|km|mg|kg|ml|mL|Hz|kHz|MHz|°C|℃|%|px|GB|MB|ms|mol|mM)\b",
    re.IGNORECASE,
)
ABBR_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,8}\b")
TERM_RE = re.compile(r"\b[a-z]+(?:[- ][a-z]+){1,3}\b")


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


def read_source(case: dict[str, Any], roots: list[Path]) -> tuple[str, str]:
    materials = case.get("materials") if isinstance(case.get("materials"), dict) else {}
    key = case.get("source") or materials.get("source") or materials.get("text")
    if not key and case.get("text"):
        return str(case["text"]), "inline"
    if not key:
        raise FileNotFoundError("case needs materials.source or text")
    path = locate(str(key), roots)
    if path is None:
        raise FileNotFoundError(f"source not found: {key}")
    if path.suffix == ".json":
        payload = load_json(path)
        if isinstance(payload, dict) and payload.get("blocks"):
            parts = [str(block.get("text") or "") for block in payload["blocks"] if block.get("in_body_flow", True)]
            return "\n\n".join(part for part in parts if part.strip()), str(path)
        if isinstance(payload, dict) and payload.get("text"):
            return str(payload["text"]), str(path)
    return path.read_text(encoding="utf-8"), str(path)


def paragraphs(text: str) -> list[str]:
    chunks = re.split(r"\n\s*\n", text.strip())
    return [squash(chunk) for chunk in chunks if squash(chunk)]


def segment_record(index: int, text: str) -> dict[str, Any]:
    units = []
    for match in UNIT_RE.finditer(text):
        units.append({"number": match.group(1), "unit": match.group(2), "surface": match.group(0)})
    return {
        "seg_id": f"s{index}",
        "text": text,
        "numbers": NUM_RE.findall(text),
        "units": units,
        "citations": [match.group(0) for pattern in CITE_RES for match in pattern.finditer(text)],
        "formulas": FORMULA_RE.findall(text),
        "abbreviations": sorted(set(ABBR_RE.findall(text))),
        "term_candidates": sorted(set(match.group(0).lower() for match in TERM_RE.finditer(text)))[:40],
    }


def build(case: dict[str, Any], roots: list[Path]) -> dict[str, Any]:
    text, origin = read_source(case, roots)
    records = [segment_record(index, chunk) for index, chunk in enumerate(paragraphs(text), start=1)]
    return {"source_path": origin, "n_segments": len(records), "segments": records}


def main() -> int:
    parser = argparse.ArgumentParser(description="Segment a source for locked translation")
    parser.add_argument("--case", required=True)
    parser.add_argument("--input-root", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    case_path = Path(args.case)
    roots = [case_path.parent]
    if args.input_root:
        roots.append(Path(args.input_root))
    roots.append(Path("/input"))
    payload = build(load_json(case_path), roots)
    write_json(Path(args.output), payload)
    print(f"segments={payload['n_segments']} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
