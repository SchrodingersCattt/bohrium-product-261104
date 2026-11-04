#!/usr/bin/env python3
"""Machine-check the slot-01 submit recipe. This script never submits.

Exit 0: Playground CLI is on PATH, the worker health check succeeded, and
submissions/01 is inside the package caps.
Exit 2: the package is fine and the worker answered, but no playground binary
was found. That is the current blocker.
Exit 1: the package or the worker check failed.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "submissions" / "01"
SKILL = ROOT / "skills" / "01-pdf-reading-order"
WORKER_HEALTH = "http://47.92.88.121:443/health"
CHALLENGE = "product-arena-08-3027d350"
TEXT_SUFFIXES = {".py", ".md", ".json", ".jsonl", ".txt", ".yaml", ".yml", ".tex", ".bib"}
MAX_TEXT_FILES = 50
MAX_TEXT_BYTES = 500 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024


def package_report(path: Path) -> dict:
    files = [item for item in path.rglob("*") if item.is_file() and "__pycache__" not in item.parts]
    text_files = []
    text_bytes = 0
    total = 0
    for item in files:
        size = item.stat().st_size
        total += size
        if item.suffix.lower() in TEXT_SUFFIXES:
            text_files.append(item)
            text_bytes += size
    problems = []
    if not (path / "SKILL.md").is_file():
        problems.append("SKILL.md missing")
    if len(text_files) > MAX_TEXT_FILES:
        problems.append(f"text files {len(text_files)} > {MAX_TEXT_FILES}")
    if text_bytes > MAX_TEXT_BYTES:
        problems.append(f"text bytes {text_bytes} > {MAX_TEXT_BYTES}")
    if total > MAX_TOTAL_BYTES:
        problems.append(f"total bytes {total} > {MAX_TOTAL_BYTES}")
    return {
        "files": len(files),
        "text_files": len(text_files),
        "text_bytes": text_bytes,
        "total_bytes": total,
        "problems": problems,
    }


def same_tree(left: Path, right: Path) -> bool:
    def listing(path: Path) -> set[tuple[str, bytes]]:
        rows = set()
        for item in path.rglob("*"):
            if not item.is_file() or "__pycache__" in item.parts:
                continue
            rows.add((str(item.relative_to(path)), item.read_bytes()))
        return rows

    return listing(left) == listing(right)


def worker_ok() -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(WORKER_HEALTH, timeout=15) as response:
            body = response.read(300).decode("utf-8", "replace")
            return response.status == 200 and "playground-worker-upload" in body, body.strip()
    except Exception as exc:
        return False, exc.__class__.__name__


def main() -> int:
    report = package_report(PACKAGE)
    report["matches_skill"] = same_tree(PACKAGE, SKILL)
    if not report["matches_skill"]:
        report["problems"].append("submissions/01 is not identical to skills/01-pdf-reading-order")
    healthy, detail = worker_ok()
    cli = shutil.which("playground")
    version = ""
    dry_run_flag = False
    if cli:
        proc = subprocess.run([cli, "--version"], check=False, text=True, capture_output=True)
        version = (proc.stdout or proc.stderr).strip().splitlines()[0] if (proc.stdout or proc.stderr) else ""
        help_proc = subprocess.run([cli, "submit", "--help"], check=False, text=True, capture_output=True)
        help_text = help_proc.stdout + help_proc.stderr
        dry_run_flag = "--dry-run" in help_text
    command = (
        "playground submit --challenge-id "
        + CHALLENGE
        + " --outputs submissions/01 --trace <session.jsonl> --dry-run"
    )
    payload = {
        "submitted": False,
        "challenge_id": CHALLENGE,
        "outputs": "submissions/01",
        "replaces_attempt": 62956,
        "worker_health_url": WORKER_HEALTH,
        "worker_ok": healthy,
        "worker_detail": detail[:180],
        "playground": cli or "",
        "playground_version": version,
        "dry_run_in_help": dry_run_flag,
        "package": report,
        "next_command": command,
    }
    print(json.dumps(payload, indent=2))
    if report["problems"] or not healthy:
        return 1
    if not cli:
        return 2
    if not dry_run_flag:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
