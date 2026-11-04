#!/usr/bin/env python3
"""Extract a research PDF into page-anchored blocks in reading order.

The sharp sub-problem is multi-column reading order plus role labels, with
every character copied from the text layer (or from an OCR/fixture box file).
Text is never invented. Image-only pages are reported, not guessed.
"""

from __future__ import annotations

import argparse
import re
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harbor import base_result, case_id_of, load_json, write_json

MARGIN_FRAC = 0.065
HEADING_RE = re.compile(
    r"^(?:(?:\d+(?:\.\d+)*)[\.\s)]+|(?:abstract|introduction|related work|"
    r"background|methods?|materials|results?|discussion|conclusion|references|"
    r"bibliography|appendix|acknowledgements?))\b",
    re.IGNORECASE,
)
CAPTION_RE = re.compile(r"^(?:figure|fig\.|table|tab\.|图|表)\s*[\dA-Za-z]", re.IGNORECASE)
FORMULA_CHARS = set("=∑∫√αβγδλμνπρστωφψΩ≤≥±×÷∞∂∇^_")


def join_lines(raw: str) -> tuple[str, bool]:
    changed = False

    def repl(match: re.Match[str]) -> str:
        nonlocal changed
        changed = True
        return match.group(1)

    text = re.sub(r"-\s*\n\s*([a-z])", repl, raw)
    text = re.sub(r"[ \t]*\n[ \t]*", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text, changed


def normalize_repeat(text: str) -> str:
    collapsed = re.sub(r"\d+", "#", text.lower())
    return re.sub(r"\s+", " ", collapsed).strip()


def median_size(blocks: list[dict[str, Any]]) -> float:
    sizes = [float(block["size"]) for block in blocks if block.get("size")]
    if not sizes:
        return 10.0
    return float(statistics.median(sizes))


def is_formula(text: str) -> bool:
    compact = text.strip()
    if not compact or len(compact) > 180:
        return False
    symbols = [char for char in compact if char in FORMULA_CHARS]
    letters = [char for char in compact if char.isalpha()]
    if len(symbols) >= 2 and len(letters) <= max(14, len(symbols) * 3) and compact.count(" ") <= 14:
        return True
    return bool(
        re.search(r"\b[A-Za-zα-ωΑ-Ω]\s*=\s*\S+", compact)
        and len(compact) < 120
        and compact.count(" ") < 12
    )


def mark_margins(pages: list[dict[str, Any]]) -> None:
    counts: dict[str, int] = {}
    for page in pages:
        seen: set[str] = set()
        for block in page["blocks"]:
            token = normalize_repeat(block["text"])
            if token and token not in seen:
                seen.add(token)
                counts[token] = counts.get(token, 0) + 1
    for page in pages:
        height = float(page["height"])
        med = median_size(page["blocks"])
        for block in page["blocks"]:
            text = block["text"].strip()
            y0, y1 = block["bbox"][1], block["bbox"][3]
            in_top = y0 <= height * MARGIN_FRAC
            in_bottom = y1 >= height * (1.0 - MARGIN_FRAC)
            if not (in_top or in_bottom):
                continue
            size = float(block.get("size") or med)
            headingish = bool(HEADING_RE.match(text)) and size >= med * 1.05 and len(text) > 8
            if headingish:
                continue
            page_num = bool(re.fullmatch(r"[\divxlcdmIVXLCDM\-\.\s]{1,8}", text))
            short = len(text) <= 90
            small = size <= med + 0.6
            repeated = counts.get(normalize_repeat(text), 0) >= 2
            if page_num or (short and small and (repeated or len(text) <= 60)):
                block["role"] = "footer" if in_bottom and not in_top else "header"
                block["role_confidence"] = 0.9 if (page_num or repeated) else 0.62


def detect_split(blocks: list[dict[str, Any]]) -> float | None:
    """Split on left-edge clusters. Short lines keep the column's left edge."""
    if len(blocks) < 2:
        return None
    left_edges = sorted(block["bbox"][0] for block in blocks)
    gap, mid = 0.0, 0.0
    for left, right in zip(left_edges, left_edges[1:]):
        if right - left > gap:
            gap = right - left
            mid = (left + right) / 2
    if gap < 48:
        return None
    left_n = sum(1 for edge in left_edges if edge < mid)
    right_n = len(left_edges) - left_n
    if left_n == 0 or right_n == 0:
        return None
    return mid


def _ysort(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(blocks, key=lambda block: (block["bbox"][1], block["bbox"][0]))


def order_narrow(blocks: list[dict[str, Any]], notes: list[float]) -> list[dict[str, Any]]:
    """Read the left left-edge cluster top-to-bottom, then the next cluster."""
    split = detect_split(blocks)
    if split is None:
        return _ysort(blocks)
    notes.append(round(split, 2))
    left = [block for block in blocks if block["bbox"][0] < split]
    right = [block for block in blocks if block["bbox"][0] >= split]
    if not left or not right:
        return _ysort(blocks)
    return order_narrow(left, notes) + order_narrow(right, notes)


def is_full_width(block: dict[str, Any], content_width: float) -> bool:
    return (block["bbox"][2] - block["bbox"][0]) >= content_width * 0.72


def order_page(blocks: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[float]]:
    body = [
        block
        for block in blocks
        if block.get("role") not in {"header", "footer"} and not block.get("suppressed")
    ]
    if not body:
        return [], []
    content_width = max(block["bbox"][2] for block in body) - min(block["bbox"][0] for block in body)
    notes: list[float] = []
    ordered: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []

    def flush() -> None:
        nonlocal pending
        if pending:
            ordered.extend(order_narrow(pending, notes))
            pending = []

    for block in sorted(body, key=lambda item: (item["bbox"][1], item["bbox"][0])):
        if content_width > 0 and is_full_width(block, content_width):
            flush()
            block["column"] = "full"
            ordered.append(block)
        else:
            pending.append(block)
    flush()
    return ordered, notes


def merge_column_lines(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Join wrapped lines after column order. Do not join across columns."""
    merged: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    def gap_ok(previous: dict[str, Any], line: dict[str, Any]) -> bool:
        if previous.get("column") != line.get("column"):
            return False
        if previous.get("role") in {"header", "footer"} or line.get("role") in {"header", "footer"}:
            return False
        space = line["bbox"][1] - previous["bbox"][3]
        # Wrapped lines in a column sit within a few points. Taller gaps are
        # separate paragraphs or formula lines, including fixture boxes.
        if space > 3.5:
            return False
        tail = ""
        parts = previous.get("raw_parts") or []
        if parts:
            tail = str(parts[-1]).rstrip()
        elif previous.get("text"):
            tail = str(previous["text"]).rstrip()
        if space > 2.0 and tail.endswith((".", "!", "?", ";")):
            return False
        if abs(line["bbox"][0] - previous["bbox"][0]) > 16:
            return False
        if previous.get("size") and line.get("size") and abs(float(previous["size"]) - float(line["size"])) > 1.5:
            return False
        return True

    for line in blocks:
        if current is not None and gap_ok(current, line):
            current["raw_parts"].append(line.get("raw_text") or line["text"])
            current["bbox"] = [
                min(current["bbox"][0], line["bbox"][0]),
                min(current["bbox"][1], line["bbox"][1]),
                max(current["bbox"][2], line["bbox"][2]),
                max(current["bbox"][3], line["bbox"][3]),
            ]
            if line.get("size") and current.get("size"):
                current["size"] = round((float(current["size"]) + float(line["size"])) / 2, 2)
        else:
            if current is not None:
                merged.append(finish_merged(current))
            current = {
                "bbox": list(line["bbox"]),
                "raw_parts": [line.get("raw_text") or line["text"]],
                "size": line.get("size"),
                "column": line.get("column"),
                "role": line.get("role"),
                "role_confidence": line.get("role_confidence"),
                "in_body_flow": line.get("in_body_flow", True),
                "rows": line.get("rows"),
                "table_index": line.get("table_index"),
            }
    if current is not None:
        merged.append(finish_merged(current))
    return merged


def finish_merged(current: dict[str, Any]) -> dict[str, Any]:
    raw = "\n".join(current.pop("raw_parts"))
    text, dehyph = join_lines(raw)
    current["raw_text"] = raw
    current["text"] = text
    current["dehyphenated"] = dehyph
    return current


def assign_column_labels(blocks: list[dict[str, Any]], splits: list[float]) -> None:
    if not splits:
        for block in blocks:
            block.setdefault("column", "single")
        return
    mid = splits[0]
    for block in blocks:
        if block.get("column") == "full":
            continue
        block["column"] = "left" if block["bbox"][0] < mid else "right"


def classify_roles(blocks: list[dict[str, Any]], med: float) -> None:
    for block in blocks:
        if block.get("role") in {"header", "footer", "table"}:
            continue
        text = block["text"].strip()
        size = float(block.get("size") or med)
        if CAPTION_RE.match(text):
            block["role"] = "caption"
            block["role_confidence"] = 0.82
        elif is_formula(text):
            block["role"] = "formula"
            block["role_confidence"] = 0.64
        elif size >= med * 1.18 and len(text) < 160:
            block["role"] = "heading"
            block["role_confidence"] = 0.76
        elif HEADING_RE.match(text) and len(text) < 160:
            block["role"] = "heading"
            block["role_confidence"] = 0.7
        elif re.match(r"^\[\d+\]\s+\S", text):
            block["role"] = "reference"
            block["role_confidence"] = 0.6
        else:
            block["role"] = "paragraph"
            block["role_confidence"] = 0.6
        if block.get("dehyphenated"):
            block["role_confidence"] = round(min(block.get("role_confidence", 0.5), 0.55), 2)


def heading_level(text: str, size: float, med: float) -> int:
    match = re.match(r"^(\d+(?:\.\d+)*)", text.strip())
    if match:
        return match.group(1).count(".") + 1
    if size >= med * 1.35:
        return 1
    return 2


def build_sections(blocks: list[dict[str, Any]], med: float) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for block in blocks:
        if block.get("role") == "heading":
            current = {
                "section_id": f"s{len(sections) + 1}",
                "title": block["text"],
                "level": heading_level(block["text"], float(block.get("size") or med), med),
                "page": block["page"],
                "block_ids": [block["block_id"]],
            }
            sections.append(current)
        elif current is not None and block.get("role") not in {"header", "footer"}:
            current["block_ids"].append(block["block_id"])
    return sections


def bbox_center_inside(block: dict[str, Any], bbox: tuple[float, float, float, float]) -> bool:
    cx = (block["bbox"][0] + block["bbox"][2]) / 2
    cy = (block["bbox"][1] + block["bbox"][3]) / 2
    return bbox[0] - 2 <= cx <= bbox[2] + 2 and bbox[1] - 2 <= cy <= bbox[3] + 2


def attach_tables(page: dict[str, Any], raw_page: Any) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    if raw_page is None or not hasattr(raw_page, "find_tables"):
        return tables
    try:
        found = raw_page.find_tables()
    except Exception as exc:
        page.setdefault("warnings", []).append(f"table detection failed: {exc}")
        return tables
    for index, table in enumerate(getattr(found, "tables", []) or [], start=1):
        try:
            rows = table.extract()
            bbox = tuple(float(value) for value in table.bbox)
        except Exception as exc:
            page.setdefault("warnings", []).append(f"table extract failed: {exc}")
            continue
        clean_rows = []
        for row in rows or []:
            clean_rows.append([("" if cell is None else str(cell).strip()) for cell in row])
        if not any(any(cell for cell in row) for row in clean_rows):
            continue
        covered = [block for block in page["blocks"] if bbox_center_inside(block, bbox)]
        for block in covered:
            block["role"] = "table-cell"
            block["suppressed"] = True
        flat = " | ".join(cell for row in clean_rows for cell in row if cell)
        synthetic = {
            "bbox": [round(bbox[0], 2), round(bbox[1], 2), round(bbox[2], 2), round(bbox[3], 2)],
            "text": flat,
            "raw_text": flat,
            "size": median_size(covered) if covered else median_size(page["blocks"]),
            "role": "table",
            "role_confidence": 0.7,
            "dehyphenated": False,
            "table_index": index,
            "rows": clean_rows,
        }
        page["blocks"].append(synthetic)
        tables.append(
            {
                "table_id": f"p{page['page']}-t{index}",
                "page": page["page"],
                "bbox": synthetic["bbox"],
                "rows": clean_rows,
                "n_rows": len(clean_rows),
                "n_cols": max((len(row) for row in clean_rows), default=0),
            }
        )
    return tables


def blocks_from_fitz(doc: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    pages = []
    tables: list[dict[str, Any]] = []
    warnings: list[str] = []
    for number, page in enumerate(doc, start=1):
        info = page.get_text("dict") or {}
        blocks: list[dict[str, Any]] = []
        for block in info.get("blocks", []):
            if block.get("type") != 0:
                warnings.append(f"page {number}: non-text block type {block.get('type')}")
                continue
            # MuPDF often glues both columns into one block. Keep line boxes.
            for line in block.get("lines", []):
                spans = line.get("spans") or []
                raw = "".join(span.get("text", "") for span in spans)
                text = re.sub(r"\s+", " ", raw).strip()
                if not text:
                    continue
                sizes = [float(span.get("size") or 0) for span in spans if span.get("size")]
                x0, y0, x1, y1 = line["bbox"]
                blocks.append(
                    {
                        "bbox": [round(float(x0), 2), round(float(y0), 2), round(float(x1), 2), round(float(y1), 2)],
                        "raw_text": raw,
                        "text": text,
                        "size": round(float(statistics.median(sizes)), 2) if sizes else None,
                        "dehyphenated": False,
                    }
                )
        page_record = {
            "page": number,
            "width": float(page.rect.width),
            "height": float(page.rect.height),
            "blocks": blocks,
        }
        if not blocks and not (page.get_text("text") or "").strip():
            page_record["image_only"] = True
            warnings.append(f"page {number}: no text layer")
        tables.extend(attach_tables(page_record, page))
        pages.append(page_record)
    return pages, tables, warnings


def blocks_from_pdftotext(pdf: Path) -> tuple[list[dict[str, Any]], list[str]]:
    proc = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf), "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "pdftotext failed")
    pages = []
    chunks = proc.stdout.split("\f")
    warnings = ["pdftotext fallback has no coordinates; column order is not recovered"]
    for number, chunk in enumerate(chunks, start=1):
        text = chunk.strip()
        if not text:
            continue
        pages.append(
            {
                "page": number,
                "width": 612.0,
                "height": 792.0,
                "blocks": [
                    {
                        "bbox": [72.0, 72.0, 540.0, 720.0],
                        "raw_text": text,
                        "text": re.sub(r"\s+", " ", text).strip(),
                        "size": 10.0,
                        "dehyphenated": False,
                        "role_confidence": 0.3,
                    }
                ],
            }
        )
    return pages, warnings


def blocks_from_fixture(payload: dict[str, Any]) -> list[dict[str, Any]]:
    pages = []
    for number, page in enumerate(payload.get("pages") or [], start=1):
        blocks = []
        for block in page.get("blocks") or []:
            raw = str(block.get("raw_text") or block.get("text") or "")
            text, dehyph = join_lines(raw)
            if not text:
                continue
            bbox = [float(value) for value in block["bbox"]]
            blocks.append(
                {
                    "bbox": bbox,
                    "raw_text": raw,
                    "text": text,
                    "size": float(block.get("size") or 10),
                    "dehyphenated": dehyph,
                }
            )
        pages.append(
            {
                "page": int(page.get("page") or number),
                "width": float(page.get("width") or 595),
                "height": float(page.get("height") or 842),
                "blocks": blocks,
            }
        )
    return pages


def locate(raw: str, roots: list[Path]) -> Path | None:
    candidate = Path(raw)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    for root in roots:
        found = root / raw
        if found.exists():
            return found
    return None


def assemble(pages: list[dict[str, Any]], tables: list[dict[str, Any]], source: dict[str, Any]) -> dict[str, Any]:
    mark_margins(pages)
    reading: list[dict[str, Any]] = []
    order_notes = []
    formulas = []
    unreadable = []
    cursor = 0
    for page in pages:
        if page.get("image_only"):
            unreadable.append(
                {
                    "page": page["page"],
                    "reason": "no text layer",
                    "action": "do not invent text; pass OCR boxes in fixture schema to this script",
                }
            )
        ordered, splits = order_page(page["blocks"])
        assign_column_labels(ordered, splits)
        med = median_size(page["blocks"])
        classify_roles(ordered, med)
        margins = [block for block in page["blocks"] if block.get("role") in {"header", "footer"}]
        for block in margins:
            block["column"] = "margin"
            block["in_body_flow"] = False
        for block in ordered:
            block["in_body_flow"] = True
        ordered = merge_column_lines(ordered)
        order_notes.append(
            {
                "page": page["page"],
                "mode": "columns" if splits else "single",
                "split_x": splits,
                "n_body_blocks": len(ordered),
            }
        )
        for block in ordered + margins:
            if block.get("suppressed"):
                continue
            cursor += 1
            block["block_id"] = f"p{page['page']}-b{cursor:03d}"
            block["page"] = page["page"]
            block["reading_index"] = cursor
            reading.append(block)
            if block.get("role") == "formula":
                formulas.append(
                    {
                        "formula_id": block["block_id"],
                        "page": page["page"],
                        "text": block["text"],
                        "bbox": block["bbox"],
                        "note": "surface text only; scientific meaning is not interpreted",
                    }
                )
        for table in tables:
            if table["page"] == page["page"]:
                match = next((block for block in reading if block.get("role") == "table" and block.get("bbox") == table["bbox"]), None)
                if match:
                    table["block_id"] = match["block_id"]
    med_all = median_size([block for block in reading if block.get("in_body_flow", True)])
    sections = build_sections(reading, med_all)
    body_only = [block for block in reading if block.get("in_body_flow", True)]
    for previous, nxt in zip(body_only, body_only[1:]):
        if previous["page"] + 1 == nxt["page"] and previous["text"] and previous["text"][-1] not in ".!?;:":
            if nxt["text"][:1].islower():
                nxt.setdefault("warnings", []).append("possible continuation from previous page")
    public_blocks = []
    for block in reading:
        public_blocks.append(
            {
                "block_id": block["block_id"],
                "page": block["page"],
                "reading_index": block["reading_index"],
                "in_body_flow": bool(block.get("in_body_flow", True)),
                "bbox": block["bbox"],
                "column": block.get("column", "single"),
                "role": block.get("role", "paragraph"),
                "role_confidence": block.get("role_confidence", 0.5),
                "text": block["text"],
                "raw_text": block.get("raw_text", block["text"]),
                "dehyphenated": bool(block.get("dehyphenated")),
                "warnings": block.get("warnings", []),
            }
        )
    return {
        "document": {
            "source": source,
            "n_pages": len(pages),
            "n_blocks": len(public_blocks),
        },
        "blocks": public_blocks,
        "sections": sections,
        "tables": tables,
        "formulas": formulas,
        "reading_order_notes": order_notes,
        "unreadable": unreadable,
    }


def extract(case: dict[str, Any], roots: list[Path]) -> tuple[dict[str, Any], list[str], str]:
    materials = case.get("materials") if isinstance(case.get("materials"), dict) else {}
    pdf_key = case.get("pdf") or case.get("pdf_path") or materials.get("pdf")
    fixture_key = case.get("fixture") or materials.get("fixture")
    warnings: list[str] = []
    if pdf_key:
        pdf = locate(str(pdf_key), roots)
        if pdf is None:
            raise FileNotFoundError(f"PDF not found: {pdf_key}")
        source = {"kind": "pdf", "path": str(pdf)}
        try:
            import fitz  # type: ignore

            with fitz.open(pdf) as doc:
                if getattr(doc, "is_encrypted", False) and doc.needs_pass:
                    raise PermissionError("encrypted PDF; password not provided")
                pages, tables, warnings = blocks_from_fitz(doc)
            return assemble(pages, tables, source), warnings, "pymupdf"
        except PermissionError:
            raise
        except Exception as exc:
            warnings.append(f"pymupdf failed: {exc}")
            pages, extra = blocks_from_pdftotext(pdf)
            warnings.extend(extra)
            return assemble(pages, [], source), warnings, "pdftotext"
    if fixture_key or case.get("pages"):
        if case.get("pages"):
            payload = case
            source = {"kind": "fixture", "path": "inline"}
        else:
            path = locate(str(fixture_key), roots)
            if path is None:
                raise FileNotFoundError(f"fixture not found: {fixture_key}")
            payload = load_json(path)
            source = {"kind": "fixture", "path": str(path)}
        pages = blocks_from_fixture(payload)
        return assemble(pages, [], source), warnings, "fixture"
    raise FileNotFoundError("case.json needs materials.pdf or materials.fixture")


def status_for(parsed: dict[str, Any], warnings: list[str]) -> tuple[str, str]:
    if not parsed["blocks"] and parsed["unreadable"]:
        return "undetermined", "no text layer on the provided PDF; characters were not guessed"
    if parsed["unreadable"] or any("fallback" in warning for warning in warnings):
        return "partial", "structure recovered only for pages with a text layer or reliable coordinates"
    low = [block for block in parsed["blocks"] if block.get("role_confidence", 1) < 0.5]
    if low:
        return "partial", "some blocks are low-confidence role or dehyphenation decisions"
    return "success", "text-layer blocks ordered by column bands; no text invented"


def build_result(case: dict[str, Any], roots: list[Path]) -> dict[str, Any]:
    case_id = case_id_of(case)
    try:
        parsed, warnings, backend = extract(case, roots)
    except PermissionError as exc:
        result = base_result(case_id, "refused", str(exc))
        result.update(empty_payload())
        result["limits"] = [str(exc)]
        return result
    except FileNotFoundError as exc:
        result = base_result(case_id, "refused", str(exc))
        result.update(empty_payload())
        result["limits"] = [str(exc)]
        return result
    status, reason = status_for(parsed, warnings)
    result = base_result(case_id, status, reason)
    result.update(parsed)
    result["document"]["backend"] = backend
    result["sources"] = [
        {
            "source_id": parsed["document"]["source"]["kind"],
            "path": parsed["document"]["source"]["path"],
            "locator": f"pages 1-{parsed['document']['n_pages']}",
            "quote": parsed["blocks"][0]["text"][:180] if parsed["blocks"] else "",
        }
    ]
    for item in parsed["unreadable"]:
        result["uncertainty"].append(
            {
                "item": f"page {item['page']}",
                "reason": item["reason"],
                "needs_human": True,
            }
        )
    for block in parsed["blocks"]:
        if block.get("dehyphenated"):
            result["uncertainty"].append(
                {
                    "item": block["block_id"],
                    "reason": "line-end hyphen was joined; raw_text keeps the original break",
                    "needs_human": True,
                }
            )
    for warning in warnings:
        if "non-text" in warning:
            continue
        result["uncertainty"].append({"item": "extractor", "reason": warning, "needs_human": "fallback" in warning})
    result["change_records"].append(
        {
            "id": "order-1",
            "action": "reorder",
            "before": "raw PDF block order or top-to-bottom y-sort",
            "after": "full-width bands, then left column, then right column",
            "reason": "two-column pages interleave if sorted only by vertical position",
        }
    )
    if any(block["role"] == "header" or block["role"] == "footer" for block in parsed["blocks"]):
        result["change_records"].append(
            {
                "id": "margin-1",
                "action": "label",
                "before": "running headers and page numbers mixed with body candidates",
                "after": "role header or footer, kept in blocks but excluded from section flow ordering",
                "reason": "repeated margin text and page numbers are not body paragraphs",
            }
        )
    if status != "success":
        result["limits"] = [reason] + [item["reason"] for item in parsed["unreadable"]]
    return result


def empty_payload() -> dict[str, Any]:
    return {
        "document": {},
        "blocks": [],
        "sections": [],
        "tables": [],
        "formulas": [],
        "reading_order_notes": [],
        "unreadable": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse a PDF or box fixture into reading order")
    parser.add_argument("--case", required=True)
    parser.add_argument("--work", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--input-root", default="")
    args = parser.parse_args()
    case_path = Path(args.case)
    case = load_json(case_path)
    roots = [case_path.parent]
    if args.input_root:
        roots.append(Path(args.input_root))
    roots.append(Path("/input"))
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    result = build_result(case, roots)
    output = Path(args.output)
    write_json(output, result)
    write_json(work / "result.json", result)
    print(f"wrote {output} status={result['status']} blocks={len(result['blocks'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
