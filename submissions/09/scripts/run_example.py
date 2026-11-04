#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "minimal"


def run(prose: Path | None, output: Path) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "audit_methods.py"),
        "--case",
        str(EXAMPLE / "case.json"),
        "--input-root",
        str(EXAMPLE),
        "--work",
        str(output.parent / "work"),
        "--output",
        str(output),
    ]
    if prose:
        cmd.extend(["--prose", str(prose)])
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(proc.stdout + proc.stderr)
    return json.loads(output.read_text(encoding="utf-8"))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        good = run(None, tmp_path / "result.json")
        # Dataset is honestly missing, so status is partial even when numbers match.
        if good["number_audit"]["unsupported"]:
            raise SystemExit(good["number_audit"])
        if good["datasets"][0]["status"] != "not_in_source":
            raise SystemExit(good["datasets"])
        names = {row["name"] for row in good["parameter_table"]}
        if names != {"seed", "lr", "epochs"}:
            raise SystemExit(names)
        bad_path = tmp_path / "bad.md"
        bad_path.write_text("We train for 12 epochs and report 99.\n", encoding="utf-8")
        failed = run(bad_path, tmp_path / "bad-result.json")
        if not any(item["number"] == "99" for item in failed["number_audit"]["unsupported"]):
            raise SystemExit("invented 99 was not flagged")
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
