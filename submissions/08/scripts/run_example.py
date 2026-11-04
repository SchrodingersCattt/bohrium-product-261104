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


def run(draft: Path | None, output: Path, root: Path | None = None) -> dict:
    root = root or EXAMPLE
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "audit_intro.py"),
        "--case",
        str(root / "case.json"),
        "--input-root",
        str(root),
        "--work",
        str(output.parent / "work"),
        "--output",
        str(output),
    ]
    if draft:
        cmd.extend(["--draft", str(draft)])
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
        bad = json.loads((EXAMPLE / "draft.json").read_text(encoding="utf-8"))
        bad["groups"][0]["cells"][0]["quote"] = "Method A works on every sample."
        bad_path = tmp_path / "bad.json"
        bad_path.write_text(json.dumps(bad), encoding="utf-8")
        failed = run(bad_path, tmp_path / "bad-result.json")
        if failed["status"] == "success":
            raise SystemExit("invented quote was accepted")
        bare = tmp_path / "bare"
        shutil.copytree(EXAMPLE, bare)
        (bare / "draft.json").unlink()
        drafted = run(None, tmp_path / "bare-result.json", bare)
        if drafted["status"] != "success":
            raise SystemExit(json.dumps(drafted["uncertainty"], ensure_ascii=False))
        library = json.loads((EXAMPLE / "library.json").read_text(encoding="utf-8"))
        texts = {paper["paper_id"]: paper["text"] for paper in library["papers"]}
        for group in drafted["groups"]:
            for cell in group["cells"]:
                if cell["quote"] not in texts[cell["paper_id"]]:
                    raise SystemExit(cell)
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
