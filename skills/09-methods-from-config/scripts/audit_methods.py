#!/usr/bin/env python3
"""Build a parameter table from config and logs, then flag prose numbers that are not in it."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harbor import base_result, case_id_of, load_json, write_json

NUM_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?")
LINE_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_.-]*)\s*[:=]\s*(.+?)\s*$")
DATA_KEYS = ("dataset", "data", "split", "train_split", "test_split")


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def locate(raw: str, roots: list[Path]) -> Path | None:
    path = Path(raw)
    if path.is_absolute() and path.exists():
        return path
    for root in roots:
        found = root / raw
        if found.exists():
            return found
    return None


def coerce(raw: str) -> Any:
    text = raw.strip().strip("'\"")
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+", text):
        return float(text)
    return text


def from_yaml_or_text(path: Path) -> list[dict[str, Any]]:
    rows = []
    if path.suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            for key, value in payload.items():
                if isinstance(value, (dict, list)):
                    continue
                rows.append({"name": str(key), "value": value, "unit": "", "source": str(path), "line": None})
        return rows
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = LINE_RE.match(stripped)
        if not match:
            continue
        rows.append(
            {
                "name": match.group(1),
                "value": coerce(match.group(2)),
                "unit": "",
                "source": str(path),
                "line": index,
            }
        )
    return rows


def value_strings(rows: list[dict[str, Any]]) -> set[str]:
    found = set()
    for row in rows:
        value = row["value"]
        found.add(str(value))
        if isinstance(value, float):
            found.add(f"{value:.12g}")
        if isinstance(value, int):
            found.add(str(value))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="Trace method prose back to config values")
    parser.add_argument("--case", required=True)
    parser.add_argument("--input-root", default="")
    parser.add_argument("--prose", default="")
    parser.add_argument("--work", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    case_path = Path(args.case)
    case = load_json(case_path)
    roots = [case_path.parent, Path("/input")]
    if args.input_root:
        roots.append(Path(args.input_root))
    materials = case.get("materials") if isinstance(case.get("materials"), dict) else {}
    config_key = materials.get("config_dir") or materials.get("config") or "config"
    config_path = locate(str(config_key), roots)
    rows: list[dict[str, Any]] = []
    if config_path is None:
        result = base_result(case_id_of(case), "refused", "config file or directory is missing")
        result.update(empty())
        result["limits"] = ["missing config"]
        write_json(Path(args.output), result)
        return 0
    files = [config_path] if config_path.is_file() else sorted(path for path in config_path.rglob("*") if path.suffix in {".json", ".yaml", ".yml", ".txt", ".log"})
    for path in files:
        rows.extend(from_yaml_or_text(path))
    known = value_strings(rows)
    prose_path = Path(args.prose) if args.prose else locate(str(materials.get("prose") or "prose.md"), [Path(args.work), *roots])
    prose = prose_path.read_text(encoding="utf-8") if prose_path and prose_path.exists() else ""
    flagged = []
    for match in NUM_RE.finditer(prose):
        token = match.group(0)
        if token not in known and str(float(token)) not in known:
            # 12 stays "12"; 0.001 stays "0.001". Float formatting is a second chance.
            flagged.append({"number": token, "context": squash(prose[max(0, match.start() - 30) : match.end() + 30])})
    datasets = []
    for row in rows:
        if row["name"].lower() in DATA_KEYS or "dataset" in row["name"].lower():
            datasets.append({"name": row["value"], "source": row["source"], "line": row["line"], "status": "from_config"})
    if not datasets:
        datasets.append({"name": None, "status": "not_in_source", "reason": "no dataset key in the config or logs"})
    steps = [
        {
            "step_id": f"p{index}",
            "name": row["name"],
            "value": row["value"],
            "source": row["source"],
            "line": row["line"],
        }
        for index, row in enumerate(rows, start=1)
    ]
    limitations = []
    if any(item["status"] == "not_in_source" for item in datasets):
        limitations.append({"item": "dataset", "reason": "not named in the supplied config", "needs_author": True})
    if flagged:
        limitations.append({"item": "prose numbers", "reason": "at least one number is not in the config", "needs_author": True})
    reproducibility = {
        "config_files": [str(path) for path in files],
        "parameters_extracted": len(rows),
        "command": case.get("command") or "",
        "seed_present": any(row["name"].lower() in {"seed", "random_seed"} for row in rows),
    }
    if prose_path is None or not prose:
        status, reason = "partial", "parameters are extracted; prose.md is still required"
    elif flagged:
        status, reason = "partial", "prose contains numbers that are not in the config or logs"
    elif not rows:
        status, reason = "undetermined", "no key-value parameters were found"
    elif any(item.get("status") == "not_in_source" for item in datasets):
        status, reason = "partial", "prose numbers match the config; a setup field such as the dataset is absent and was not invented"
    else:
        status, reason = "success", "every prose number matches an extracted parameter and the setup fields are present"
    result = base_result(case_id_of(case), status, reason)
    result.update(
        {
            "parameter_table": rows,
            "datasets": datasets,
            "steps": steps,
            "prose": prose,
            "number_audit": {"unsupported": flagged, "known_values": sorted(known)},
            "reproducibility": reproducibility,
            "limitations": limitations,
        }
    )
    result["sources"] = [
        {"source_id": row["name"], "path": row["source"], "locator": f"line {row['line']}", "quote": f"{row['name']}={row['value']}"}
        for row in rows
    ]
    for item in flagged:
        result["uncertainty"].append({"item": item["number"], "reason": item["context"], "needs_human": True})
    for item in limitations:
        result["uncertainty"].append({"item": item["item"], "reason": item["reason"], "needs_human": True})
    if status != "success":
        result["limits"] = [reason]
    result["change_records"].append(
        {
            "id": "methods-1",
            "action": "trace",
            "before": "prose numbers",
            "after": f"{len(rows)} config values; {len(flagged)} unsupported",
            "reason": "a smooth paragraph can introduce a number that no config contains",
        }
    )
    Path(args.work).mkdir(parents=True, exist_ok=True)
    write_json(Path(args.output), result)
    print(f"status={status} params={len(rows)} unsupported={len(flagged)}")
    return 0


def empty() -> dict[str, Any]:
    return {
        "parameter_table": [],
        "datasets": [],
        "steps": [],
        "prose": "",
        "number_audit": {},
        "reproducibility": {},
        "limitations": [],
    }


if __name__ == "__main__":
    raise SystemExit(main())
