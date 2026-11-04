#!/usr/bin/env python3
"""Install slot 01 the way the contest contract describes and run it.

The official grader zero on attempts 62955-62964 is a worker-queue guard.
This script does not submit. It checks that the skill, once placed at the
contract install path, writes a complete /app/output/result.json.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "01-pdf-reading-order"
REQUIRED = (
    "case_id",
    "status",
    "status_reason",
    "sources",
    "uncertainty",
    "change_records",
    "document",
    "blocks",
    "sections",
    "tables",
    "formulas",
    "reading_order_notes",
    "unreadable",
)


def main() -> int:
    if not (SKILL / "SKILL.md").is_file():
        print("missing skill", SKILL, file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory(prefix="weekly-skill-") as tmp:
        base = Path(tmp)
        install = base / "skills" / "weekly-skill"
        input_dir = base / "input"
        work = base / "app" / "work"
        output = base / "app" / "output" / "result.json"
        shutil.copytree(SKILL, install)
        input_dir.mkdir()
        for item in (install / "examples" / "minimal").iterdir():
            if item.is_file():
                shutil.copy2(item, input_dir / item.name)
        work.mkdir(parents=True)
        output.parent.mkdir(parents=True)
        proc = subprocess.run(
            [
                sys.executable,
                str(install / "scripts" / "parse_pdf.py"),
                "--case",
                str(input_dir / "case.json"),
                "--input-root",
                str(input_dir),
                "--work",
                str(work),
                "--output",
                str(output),
            ],
            check=False,
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            print(proc.stdout)
            print(proc.stderr, file=sys.stderr)
            return proc.returncode
        val = subprocess.run(
            [
                sys.executable,
                str(install / "scripts" / "validate_result.py"),
                str(output),
                "--contract",
                str(install / "resources" / "output_contract.json"),
                "--case",
                str(input_dir / "case.json"),
            ],
            check=False,
            text=True,
            capture_output=True,
        )
        if val.returncode != 0:
            print(val.stdout)
            print(val.stderr, file=sys.stderr)
            return val.returncode
        payload = json.loads(output.read_text(encoding="utf-8"))
        missing = [key for key in REQUIRED if key not in payload]
        if missing or payload.get("status") not in {"success", "partial", "undetermined", "refused"}:
            print("incomplete result", missing, payload.get("status"), file=sys.stderr)
            return 1
        if not payload.get("blocks"):
            print("result has no blocks", file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "rehearsal": "slot-01",
                    "install_layout": "skills/weekly-skill",
                    "output": "app/output/result.json",
                    "status": payload["status"],
                    "case_id": payload["case_id"],
                    "blocks": len(payload["blocks"]),
                    "validator": "ok",
                    "submitted": False,
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
