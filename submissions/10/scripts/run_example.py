#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "minimal"


def compile_case(case: Path, output: Path) -> dict:
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts" / "compile_tex.py"),
            "--case",
            str(case),
            "--input-root",
            str(EXAMPLE),
            "--work",
            str(output.parent / "work"),
            "--output",
            str(output),
        ],
        check=False,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stdout + proc.stderr)
    return json.loads(output.read_text(encoding="utf-8"))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        good = compile_case(EXAMPLE / "case.json", tmp_path / "good.json")
        if good["compile"]["exit_code"] != 0:
            raise SystemExit(good["artifacts"].get("log_tail", "")[-500:])
        if not any(item["label"] == "tab:unused" for item in good["hygiene"]):
            raise SystemExit(good["hygiene"])
        broken = compile_case(EXAMPLE / "broken-case.json", tmp_path / "broken.json")
        if not any(item.get("line") == 4 for item in broken["errors"]):
            raise SystemExit(json.dumps(broken["errors"], ensure_ascii=False, indent=2))
        if broken["artifacts"].get("pdf_written"):
            raise SystemExit("broken tex produced a pdf")
        check = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate_result.py"),
                str(tmp_path / "good.json"),
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
    wrapped = {
        "label": "EXAMPLE ONLY. Not an official contest case and not a prepared answer.",
        "clean_compile": good,
        "broken_compile": {
            "case_id": broken["case_id"],
            "status": broken["status"],
            "errors": broken["errors"],
            "pdf_written": broken["artifacts"].get("pdf_written"),
        },
    }
    destination = EXAMPLE / "example_result.json"
    destination.write_text(json.dumps(wrapped, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"example ok -> {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
