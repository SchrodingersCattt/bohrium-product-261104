#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "minimal"


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        output = tmp_path / "result.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "manage_citations.py"),
                "--case",
                str(EXAMPLE / "case.json"),
                "--input-root",
                str(EXAMPLE),
                "--work",
                str(tmp_path / "work"),
                "--output",
                str(output),
            ],
            check=False,
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            raise SystemExit(proc.stdout + proc.stderr)
        result = json.loads(output.read_text(encoding="utf-8"))
        if result["status"] != "partial":
            raise SystemExit(result["status_reason"])
        if result["key_to_number"].get("smith2020") != 1 or result["key_to_number"].get("other") != 2:
            raise SystemExit(result["key_to_number"])
        if result["redirect"].get("smith2020arxiv") != "smith2020":
            raise SystemExit(result["redirect"])
        if "missing" not in result["unknown_keys"]:
            raise SystemExit(result["unknown_keys"])
        if "smithclash" in result["key_to_number"]:
            raise SystemExit("uncited conflicting record was numbered")
        if not result["conflicts"]:
            raise SystemExit("DOI conflict was merged or ignored")
        gbt = next(item["gbt7714_simplified"] for item in result["references"] if item["key"] == "smith2020")
        if "[J]" not in gbt or "10.1000/example.1" not in gbt:
            raise SystemExit(gbt)
        check = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate_result.py"),
                str(output),
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
    destination = EXAMPLE / "example_result.json"
    destination.write_text(
        json.dumps(
            {"label": "EXAMPLE ONLY. Not an official contest case and not a prepared answer.", "result": result},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"example ok -> {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
