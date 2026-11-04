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
                str(ROOT / "scripts" / "build_graph.py"),
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
        if result["status"] != "success":
            raise SystemExit(json.dumps(result["uncertainty"], ensure_ascii=False, indent=2))
        nodes = result["graph"]["nodes"]
        widenet = [
            node
            for node in nodes
            if node["surface"].casefold() == "widenet" or "widenet" in {alias.casefold() for alias in node.get("aliases") or []}
        ]
        if len(widenet) != 1:
            raise SystemExit(f"expected one WideNet node, got {widenet}")
        sources = {item["source_id"] for item in widenet[0]["evidence"]}
        if sources != {"primary", "secondary"}:
            raise SystemExit(f"WideNet evidence sources: {sources}")
        scores = [node for node in nodes if node["type"] == "metric"]
        if len(scores) < 2:
            raise SystemExit("accuracy values were merged")
        cnn = [node for node in nodes if node["surface"] == "CNN"]
        if not cnn or cnn[0]["node_id"] == widenet[0]["node_id"]:
            raise SystemExit("CNN was merged into WideNet")
        if any(item.get("surface") == "ImageNet" for item in nodes):
            raise SystemExit("ImageNet was kept without support")
        if len(result["queries"]) < 3:
            raise SystemExit("queries were not executed")
        dois = [doc.get("doi") for doc in result["documents"]]
        if dois[0] == dois[1] or None in dois:
            raise SystemExit(f"DOI mixup: {dois}")
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
