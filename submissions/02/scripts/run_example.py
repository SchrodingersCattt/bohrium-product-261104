#!/usr/bin/env python3
"""Run the labeled translation example and a failing control."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "minimal"


def run(case: Path, translation: Path | None, output: Path) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "audit_translation.py"),
        "--case",
        str(case),
        "--input-root",
        str(EXAMPLE),
        "--work",
        str(output.parent / "work"),
        "--output",
        str(output),
    ]
    if translation:
        cmd.extend(["--translation", str(translation)])
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(proc.stdout + proc.stderr)
    return json.loads(output.read_text(encoding="utf-8"))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        good = run(EXAMPLE / "case.json", None, tmp_path / "result.json")
        if good["status"] != "success":
            raise SystemExit(json.dumps(good["audit"], ensure_ascii=False, indent=2))
        if good["segments"][0]["translation"].index("10") > good["segments"][0]["translation"].index("结合亲和力"):
            pass
        bad_path = tmp_path / "bad.json"
        bad_payload = json.loads((EXAMPLE / "translation.json").read_text(encoding="utf-8"))
        bad_payload["segments"][0]["translation"] = "结合力很强 (Smith, 2020)。公式 $E = mc^2$ 在 25 °C 下成立。"
        bad_path.write_text(json.dumps(bad_payload), encoding="utf-8")
        bad = run(EXAMPLE / "case.json", bad_path, tmp_path / "bad-result.json")
        if bad["status"] == "success" or not bad["audit"]["issues"]:
            raise SystemExit("dropped number and locked term were not caught")
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
    wrapped = {
        "label": "EXAMPLE ONLY. Not an official contest case and not a prepared answer.",
        "result": good,
    }
    destination = EXAMPLE / "example_result.json"
    destination.write_text(json.dumps(wrapped, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"example ok -> {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
