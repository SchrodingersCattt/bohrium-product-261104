#!/usr/bin/env python3
"""Run the labeled minimal example and check reading-order invariants."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "minimal"
SCRIPTS = ROOT / "scripts"


def body_text(result: dict) -> str:
    blocks = [block for block in result["blocks"] if block.get("in_body_flow")]
    blocks.sort(key=lambda block: block["reading_index"])
    return "\n".join(block["text"] for block in blocks)


def assert_order(result: dict, where: str) -> None:
    text = body_text(result)
    if text.index("LEFT-ANCHOR") > text.index("RIGHT-ANCHOR"):
        raise SystemExit(f"{where}: right column was read before the left column")
    if "PAGE2-LEFT" in text and text.index("PAGE2-LEFT") > text.index("PAGE2-RIGHT"):
        raise SystemExit(f"{where}: page 2 columns are out of order")
    headers = [block for block in result["blocks"] if block["role"] == "header"]
    if not headers:
        raise SystemExit(f"{where}: running header was not labeled")
    if any(block.get("in_body_flow") and "Example Journal" in block["text"] for block in result["blocks"]):
        raise SystemExit(f"{where}: running header entered the body flow")
    formulas = " ".join(item["text"] for item in result["formulas"])
    if "E = mc^2" not in formulas:
        raise SystemExit(f"{where}: formula span was not kept")


def run_case(case: Path, root: Path, output: Path) -> dict:
    work = output.parent / "work"
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "parse_pdf.py"),
            "--case",
            str(case),
            "--work",
            str(work),
            "--output",
            str(output),
            "--input-root",
            str(root),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stdout + proc.stderr)
    return json.loads(output.read_text(encoding="utf-8"))


def build_pdf(fixture: dict, pdf_path: Path) -> None:
    import fitz

    doc = fitz.open()
    for spec in fixture["pages"]:
        page = doc.new_page(width=spec["width"], height=spec["height"])
        for block in spec["blocks"]:
            size = float(block.get("size") or 10)
            rect = fitz.Rect(*block["bbox"])
            if rect.height < size * 1.35:
                rect.y1 = rect.y0 + size * 1.35
            overflow = page.insert_textbox(rect, block["text"], fontsize=size, fontname="times-roman", align=0)
            if overflow < 0:
                page.insert_text((block["bbox"][0], block["bbox"][1] + size), block["text"], fontsize=size, fontname="times-roman")
    doc.save(pdf_path)
    doc.close()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        fixture_result = run_case(EXAMPLE / "case.json", EXAMPLE, tmp_path / "fixture-result.json")
        assert_order(fixture_result, "fixture")
        check = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "validate_result.py"),
                str(tmp_path / "fixture-result.json"),
                "--contract",
                str(ROOT / "resources" / "output_contract.json"),
                "--case",
                str(EXAMPLE / "case.json"),
            ],
            check=False,
            text=True,
            capture_output=True,
        )
        if check.returncode != 0:
            raise SystemExit(check.stdout + check.stderr)
        fixture = json.loads((EXAMPLE / "fixture_spec.json").read_text(encoding="utf-8"))
        pdf_path = tmp_path / "columns.pdf"
        build_pdf(fixture, pdf_path)
        pdf_case = {
            "case_id": "example-min-pdf-rendered",
            "label": "EXAMPLE ONLY. Rendered from the text fixture.",
            "materials": {"pdf": str(pdf_path)},
        }
        case_path = tmp_path / "pdf-case.json"
        case_path.write_text(json.dumps(pdf_case), encoding="utf-8")
        pdf_result = run_case(case_path, tmp_path, tmp_path / "pdf-result.json")
        assert_order(pdf_result, "pdf")
    wrapped = {
        "label": "EXAMPLE ONLY. Not an official contest case and not a prepared answer.",
        "result": fixture_result,
    }
    destination = EXAMPLE / "example_result.json"
    destination.write_text(json.dumps(wrapped, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"example ok -> {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
