#!/usr/bin/env python3
"""Install each skill the way the contest contract describes and run it.

The official grader zero on attempts 62955-62964 is a worker-queue guard.
This script does not submit. It places one skill at skills/weekly-skill,
copies the labeled example into input/, and checks that the entrypoint
writes app/output/result.json. A second pass drops the model sidecar for
slots that can still finish from the source.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".md", ".json", ".jsonl", ".txt", ".yaml", ".yml", ".tex", ".bib"}
MAX_TEXT_FILES = 50
MAX_TEXT_BYTES = 500 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024
ENVELOPE = (
    "case_id",
    "status",
    "status_reason",
    "sources",
    "uncertainty",
    "change_records",
)
STATUSES = {"success", "partial", "undetermined", "refused"}
PAIRS = (
    ("01", "01-pdf-reading-order"),
    ("02", "02-literature-term-lock"),
    ("03", "03-section-evidence-notes"),
    ("04", "04-nanopub-assertions"),
    ("05", "05-literature-kg"),
    ("06", "06-academic-polish"),
    ("07", "07-citation-bibliography"),
    ("08", "08-intro-related-work"),
    ("09", "09-methods-from-config"),
    ("10", "10-latex-compile"),
)
# script, full-example status, sidecar files omitted on the bare pass, bare status
SLOTS = (
    ("01", "scripts/parse_pdf.py", "success", (), None),
    ("02", "scripts/audit_translation.py", "success", ("translation.json",), "partial"),
    ("03", "scripts/audit_notes.py", "success", ("notes.json",), "success"),
    ("04", "scripts/audit_nanopub.py", "success", ("assertions.json",), "partial"),
    ("05", "scripts/build_graph.py", "success", ("candidates.json", "queries.json"), "success"),
    ("06", "scripts/audit_edits.py", "success", ("edits.json",), "success"),
    ("07", "scripts/manage_citations.py", "partial", (), None),
    ("08", "scripts/audit_intro.py", "success", ("draft.json",), "success"),
    ("09", "scripts/audit_methods.py", "partial", ("prose.md",), "partial"),
    # The labeled manuscript compiles, then stays partial because tab:unused is never referenced.
    ("10", "scripts/compile_tex.py", "partial", (), None),
)


def listing(path: Path) -> dict[str, bytes]:
    rows: dict[str, bytes] = {}
    for item in path.rglob("*"):
        if item.is_file() and "__pycache__" not in item.parts:
            rows[str(item.relative_to(path))] = item.read_bytes()
    return rows


def package_problems(slot: str, skill_name: str) -> list[str]:
    skill = ROOT / "skills" / skill_name
    package = ROOT / "submissions" / slot
    problems = []
    if not (skill / "SKILL.md").is_file():
        problems.append("SKILL.md missing")
    files = listing(skill)
    if files != listing(package):
        problems.append("submissions tree is not identical to skills tree")
    text_files = 0
    text_bytes = 0
    total = 0
    for rel, data in files.items():
        total += len(data)
        if Path(rel).suffix.lower() in TEXT_SUFFIXES:
            text_files += 1
            text_bytes += len(data)
    if text_files > MAX_TEXT_FILES:
        problems.append(f"text files {text_files} > {MAX_TEXT_FILES}")
    if text_bytes > MAX_TEXT_BYTES:
        problems.append(f"text bytes {text_bytes} > {MAX_TEXT_BYTES}")
    if total > MAX_TOTAL_BYTES:
        problems.append(f"total bytes {total} > {MAX_TOTAL_BYTES}")
    return problems


def copy_example(skill: Path, input_dir: Path, omit: tuple[str, ...]) -> None:
    example = skill / "examples" / "minimal"
    skip = set(omit) | {"example_result.json"}
    for item in example.iterdir():
        if item.is_file() and item.name not in skip:
            shutil.copy2(item, input_dir / item.name)


def run_installed(skill_name: str, script: str, omit: tuple[str, ...]) -> tuple[dict, str]:
    skill = ROOT / "skills" / skill_name
    with tempfile.TemporaryDirectory(prefix="weekly-skill-") as tmp:
        base = Path(tmp)
        install = base / "skills" / "weekly-skill"
        input_dir = base / "input"
        work = base / "app" / "work"
        output = base / "app" / "output" / "result.json"
        shutil.copytree(skill, install, ignore=shutil.ignore_patterns("__pycache__"))
        input_dir.mkdir()
        copy_example(install, input_dir, omit)
        work.mkdir(parents=True)
        output.parent.mkdir(parents=True)
        proc = subprocess.run(
            [
                sys.executable,
                str(install / script),
                "--case",
                str(input_dir / "case.json"),
                "--input-root",
                str(input_dir),
                "--work",
                str(work),
                "--output",
                str(output),
            ],
            check=False,
            text=True,
            capture_output=True,
            timeout=180,
        )
        if proc.returncode != 0 or not output.is_file():
            detail = (proc.stdout + proc.stderr).strip() or "no result.json"
            raise RuntimeError(detail[-800:])
        val = subprocess.run(
            [
                sys.executable,
                str(install / "scripts" / "validate_result.py"),
                str(output),
                "--contract",
                str(install / "resources" / "output_contract.json"),
                "--case",
                str(input_dir / "case.json"),
            ],
            check=False,
            text=True,
            capture_output=True,
            timeout=60,
        )
        if val.returncode != 0:
            raise RuntimeError((val.stdout + val.stderr).strip()[-800:])
        payload = json.loads(output.read_text(encoding="utf-8"))
        missing = [key for key in ENVELOPE if key not in payload]
        if missing:
            raise RuntimeError(f"incomplete result {missing}")
        if payload.get("status") not in STATUSES:
            raise RuntimeError(f"bad status {payload.get('status')}")
        return payload, "ok"


def extra_ok(slot: str, mode: str, payload: dict) -> str | None:
    if slot == "01" and mode == "full" and not payload.get("blocks"):
        return "result has no blocks"
    if slot == "02" and mode == "bare":
        if not payload.get("segments"):
            return "bare translation produced no segments"
        if "translation" not in " ".join(payload.get("limits") or []):
            return "bare translation did not record the missing file"
    if slot == "04" and mode == "bare" and payload.get("assertions"):
        return "assertions were minted without a model file"
    if slot == "05" and mode == "bare" and len(payload.get("queries") or []) < 3:
        return "harvested graph did not run default queries"
    if slot == "06" and mode == "bare":
        edits = payload.get("edits") or []
        if not edits or any(item.get("edit_type") != "unchanged" for item in edits):
            return "missing edits file did not keep the source"
    if slot == "09" and not str(payload.get("prose") or "").strip():
        return "methods prose is empty"
    if slot == "10" and mode == "full":
        compile_info = payload.get("compile") or {}
        if compile_info.get("exit_code") != 0 or not (payload.get("artifacts") or {}).get("pdf_written"):
            return "pdflatex did not write a pdf"
        labels = {item.get("label") for item in payload.get("hygiene") or []}
        if "tab:unused" not in labels:
            return "uncited table label was not reported"
    return None


def rehearse_slot(slot: str, skill_name: str, script: str, expect: str, omit: tuple[str, ...], bare_expect: str | None) -> list[dict]:
    rows = []
    modes = [("full", (), expect)]
    if bare_expect is not None:
        modes.append(("bare", omit, bare_expect))
    for mode, skipped, wanted in modes:
        try:
            payload, validator = run_installed(skill_name, script, skipped)
            problem = extra_ok(slot, mode, payload)
            if payload.get("status") != wanted:
                problem = f"status {payload.get('status')} != {wanted}"
            rows.append(
                {
                    "slot": slot,
                    "mode": mode,
                    "status": payload.get("status"),
                    "case_id": payload.get("case_id"),
                    "validator": validator if problem is None else "fail",
                    "problem": problem,
                    "submitted": False,
                }
            )
        except (RuntimeError, subprocess.TimeoutExpired, OSError, json.JSONDecodeError) as exc:
            rows.append(
                {
                    "slot": slot,
                    "mode": mode,
                    "status": None,
                    "validator": "fail",
                    "problem": str(exc),
                    "submitted": False,
                }
            )
    return rows


def main() -> int:
    by_slot = {slot: name for slot, name in PAIRS}
    failed = False
    reports = []
    for slot, skill_name in PAIRS:
        problems = package_problems(slot, skill_name)
        reports.append({"slot": slot, "package_problems": problems})
        if problems:
            failed = True
    for slot, script, expect, omit, bare_expect in SLOTS:
        for row in rehearse_slot(slot, by_slot[slot], script, expect, omit, bare_expect):
            reports.append(row)
            if row.get("problem") or row.get("validator") != "ok":
                failed = True
    print(json.dumps({"rehearsal": "slots-01-10", "submitted": False, "rows": reports}, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
