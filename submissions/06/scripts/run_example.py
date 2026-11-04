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


def run(edits: Path | None, output: Path, root: Path | None = None) -> dict:
    root = root or EXAMPLE
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "audit_edits.py"),
        "--case",
        str(root / "case.json"),
        "--input-root",
        str(root),
        "--work",
        str(output.parent / "work"),
        "--output",
        str(output),
    ]
    if edits:
        cmd.extend(["--edits", str(edits)])
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True)
    if proc.returncode != 0:
        raise SystemExit(proc.stdout + proc.stderr)
    return json.loads(output.read_text(encoding="utf-8"))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        good = run(None, tmp_path / "result.json")
        if good["status"] != "success":
            raise SystemExit(json.dumps(good["uncertainty"], ensure_ascii=False, indent=2))
        if "may" not in good["revised_text"] or "10 mg/L" not in good["revised_text"]:
            raise SystemExit(good["revised_text"])
        bad = json.loads((EXAMPLE / "edits.json").read_text(encoding="utf-8"))
        bad["edits"][0]["revised"] = "The model proves it reaches 10 mg/L [1]."
        bad["edits"][0]["edit_type"] = "clarity"
        bad["edits"][0]["reason"] = "stronger wording"
        bad_path = tmp_path / "bad.json"
        bad_path.write_text(json.dumps(bad), encoding="utf-8")
        failed = run(bad_path, tmp_path / "bad-result.json")
        if "proves" in failed["revised_text"] or failed["status"] == "success":
            raise SystemExit("strengthening edit was applied")
        bare = tmp_path / "bare"
        shutil.copytree(EXAMPLE, bare)
        (bare / "edits.json").unlink()
        kept = run(None, tmp_path / "bare-result.json", bare)
        if kept["status"] != "success" or "10 mg/L" not in kept["revised_text"] or "may" not in kept["revised_text"]:
            raise SystemExit("missing edits file did not keep the source")
        if any(edit["edit_type"] != "unchanged" for edit in kept["edits"]):
            raise SystemExit(kept["edits"])
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
