#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "minimal"


def run(assertions: Path | None, output: Path) -> dict:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "audit_nanopub.py"),
        "--case",
        str(EXAMPLE / "case.json"),
        "--input-root",
        str(EXAMPLE),
        "--work",
        str(output.parent / "work"),
        "--output",
        str(output),
    ]
    if assertions:
        cmd.extend(["--assertions", str(assertions)])
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(proc.stdout + proc.stderr)
    return json.loads(output.read_text(encoding="utf-8"))


def main() -> int:
    patterns = (ROOT / "resources" / "assertion_patterns.jsonl").read_text(encoding="utf-8").splitlines()
    if len([line for line in patterns if line.strip()]) != 20:
        raise SystemExit("expected 20 assertion patterns")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        good = run(None, tmp_path / "result.json")
        if good["status"] != "success":
            raise SystemExit(json.dumps(good["quality_checks"], ensure_ascii=False, indent=2))
        if len(good["spans"]) != 3:
            raise SystemExit(f"expected 3 spans, got {good['spans']}")
        bad = json.loads((EXAMPLE / "assertions.json").read_text(encoding="utf-8"))
        bad["assertions"] = [
            {
                "assertion_id": "wide",
                "span_id": "sp1",
                "subject": "Widget-A",
                "relation": "uses",
                "object": "ToySet",
                "assertion_text": "Widget-A uses ToySet; Widget-A reports accuracy 0.50.",
                "evidence_quote": "Widget-A uses ToySet",
                "evidence_kind": "direct",
                "provenance": bad["assertions"][0]["provenance"],
            }
        ]
        bad["rejected_spans"] = []
        bad_path = tmp_path / "bad.json"
        bad_path.write_text(json.dumps(bad), encoding="utf-8")
        failed = run(bad_path, tmp_path / "bad-result.json")
        checks = {item["check"] for item in failed["quality_checks"]}
        if "too_wide" not in checks or "span_not_accounted" not in checks:
            raise SystemExit(f"wide assertion was not caught: {checks}")
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
