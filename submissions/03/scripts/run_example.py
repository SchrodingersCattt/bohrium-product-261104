#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "minimal"


def audit(notes: Path | None, output: Path, root: Path | None = None) -> dict:
    root = root or EXAMPLE
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "audit_notes.py"),
        "--case",
        str(root / "case.json"),
        "--input-root",
        str(root),
        "--work",
        str(output.parent / "work"),
        "--output",
        str(output),
    ]
    if notes:
        cmd.extend(["--notes", str(notes)])
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(proc.stdout + proc.stderr)
    return json.loads(output.read_text(encoding="utf-8"))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        good = audit(None, tmp_path / "result.json")
        if good["status"] != "success":
            raise SystemExit(json.dumps(good.get("field_gaps"), ensure_ascii=False))
        bad = json.loads((EXAMPLE / "notes.json").read_text(encoding="utf-8"))
        bad["cards"][3]["evidence_quote"] = "Accuracy was 0.99"
        bad_path = tmp_path / "bad.json"
        bad_path.write_text(json.dumps(bad), encoding="utf-8")
        failed = audit(bad_path, tmp_path / "bad-result.json")
        if failed["status"] == "success":
            raise SystemExit("invented accuracy was accepted")
        bare = tmp_path / "bare"
        shutil.copytree(EXAMPLE, bare)
        (bare / "notes.json").unlink()
        drafted = audit(None, tmp_path / "bare-result.json", bare)
        if drafted["status"] != "success" or drafted["field_gaps"]:
            raise SystemExit(json.dumps(drafted.get("field_gaps"), ensure_ascii=False))
        quotes = {point["evidence_quote"] for point in drafted["knowledge_points"]}
        if "0.50" not in " ".join(quotes) or "0.99" in " ".join(quotes):
            raise SystemExit(sorted(quotes))
        check = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "validate_result.py"),
                str(tmp_path / "result.json"),
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
            {"label": "EXAMPLE ONLY. Not an official contest case and not a prepared answer.", "result": good},
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
