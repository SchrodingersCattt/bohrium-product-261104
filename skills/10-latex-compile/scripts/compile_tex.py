#!/usr/bin/env python3
"""Compile a TeX file with pdflatex and map log errors back to file and line.

Figure and table label checks are a small local gate. They are not doc-forge
and they do not replace the compiler.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harbor import base_result, case_id_of, load_json, write_json

LABEL_RE = re.compile(r"\\label\{(?P<label>(?P<kind>fig|tab):[^}]+)\}")
REF_RE = re.compile(r"\\ref\*?\{(?P<label>[^}]+)\}")
CITE_RE = re.compile(r"\\cite[a-zA-Z*]*\{([^}]+)\}")
BIB_KEY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)", re.IGNORECASE)


def strip_comments(text: str) -> str:
    kept = []
    for line in text.splitlines():
        cut = len(line)
        escaped = False
        for index, char in enumerate(line):
            if char == "%" and not escaped:
                cut = index
                break
            escaped = char == "\\" and not escaped
            if char != "\\":
                escaped = False
        kept.append(line[:cut])
    return "\n".join(kept)


def locate(raw: str, roots: list[Path]) -> Path | None:
    path = Path(raw)
    if path.is_absolute() and path.exists():
        return path
    for root in roots:
        found = root / raw
        if found.exists():
            return found
    return None


def hygiene(main: Path, roots: list[Path]) -> list[dict[str, str]]:
    text = strip_comments(main.read_text(encoding="utf-8"))
    # Include same-directory inputs only. Do not walk the whole disk.
    files = {main}
    for match in re.finditer(r"\\(?:input|include)\{([^}]+)\}", text):
        name = match.group(1)
        if not name.endswith(".tex"):
            name += ".tex"
        found = locate(name, [main.parent, *roots])
        if found:
            files.add(found)
    labels: dict[str, str] = {}
    refs: set[str] = set()
    issues = []
    for path in files:
        body = strip_comments(path.read_text(encoding="utf-8"))
        for match in LABEL_RE.finditer(body):
            label = match.group("label")
            if label in labels:
                issues.append({"kind": "duplicate_label", "label": label, "message": f"also in {labels[label]}"})
            labels[label] = path.name
        for match in REF_RE.finditer(body):
            refs.add(match.group("label"))
    for label in sorted(refs):
        if label.startswith(("fig:", "tab:")) and label not in labels:
            issues.append({"kind": "undefined_label", "label": label, "message": "referenced but not defined"})
    for label, source in labels.items():
        if label.startswith(("fig:", "tab:")) and label not in refs:
            issues.append({"kind": "uncited_float", "label": label, "message": f"defined in {source} and never referenced"})
    cite_keys = []
    for match in CITE_RE.finditer(text):
        cite_keys.extend(part.strip() for part in match.group(1).split(",") if part.strip())
    if cite_keys:
        bibs = list(main.parent.glob("*.bib"))
        known: set[str] = set()
        for bib in bibs:
            known.update(BIB_KEY_RE.findall(bib.read_text(encoding="utf-8")))
        if not bibs:
            issues.append({"kind": "missing_bib", "label": "", "message": "manuscript cites keys but no .bib sits beside it"})
        else:
            for key in sorted(set(cite_keys) - known):
                issues.append({"kind": "unknown_cite", "label": key, "message": "not in the local bib file"})
    if "\\documentclass" not in text or "\\begin{document}" not in text or "\\end{document}" not in text:
        issues.append({"kind": "structure", "label": "", "message": "missing documentclass or document environment"})
    return issues


def parse_log(log_text: str, main_name: str) -> list[dict[str, Any]]:
    errors = []
    current = ""
    current_file = main_name
    for line in log_text.splitlines():
        opened = re.search(r"\(([^()\s]+\.tex)", line)
        if opened:
            current_file = Path(opened.group(1)).name
        if line.startswith("!"):
            current = line[1:].strip()
        match = re.match(r"l\.(\d+)\b", line)
        if match and current:
            errors.append({"file": current_file, "line": int(match.group(1)), "message": current})
            current = ""
        warning = re.search(r"LaTeX Warning:\s+(.*)", line)
        if warning and ("undefined" in warning.group(1).lower() or "citation" in warning.group(1).lower()):
            errors.append({"file": current_file, "line": None, "message": warning.group(1).strip()})
    return errors


def compile_once(main: Path, work: Path) -> tuple[int, str, Path | None]:
    binary = shutil.which("pdflatex")
    if not binary:
        return 127, "pdflatex not on PATH", None
    work.mkdir(parents=True, exist_ok=True)
    # Copy sources so aux files stay in the work directory.
    for path in main.parent.iterdir():
        if path.suffix.lower() in {".tex", ".bib", ".cls", ".sty"} and path.is_file():
            target = work / path.name
            if path.resolve() != target.resolve():
                target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    proc = subprocess.run(
        [binary, "-interaction=nonstopmode", "-halt-on-error", "-output-directory", str(work), main.name],
        cwd=work,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    log_path = work / f"{main.stem}.log"
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else proc.stdout + proc.stderr
    pdf = work / f"{main.stem}.pdf"
    return proc.returncode, log_text, pdf if pdf.exists() else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile TeX and record line-mapped errors")
    parser.add_argument("--case", required=True)
    parser.add_argument("--input-root", default="")
    parser.add_argument("--work", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    case_path = Path(args.case)
    case = load_json(case_path)
    roots = [case_path.parent, Path("/input")]
    if args.input_root:
        roots.append(Path(args.input_root))
    materials = case.get("materials") if isinstance(case.get("materials"), dict) else {}
    main_path = locate(str(materials.get("main") or case.get("main") or "main.tex"), roots)
    if main_path is None:
        result = base_result(case_id_of(case), "refused", "main TeX file is missing")
        result.update(empty())
        result["limits"] = ["missing main.tex"]
        write_json(Path(args.output), result)
        return 0
    issues = hygiene(main_path, roots)
    work = Path(args.work) / "build"
    code, log_text, pdf = compile_once(main_path, work)
    parsed = parse_log(log_text, main_path.name) if code != 127 else []
    # A second pass only if the first pass produced a PDF. References need it.
    passes = 1
    if code == 0 and pdf is not None:
        code, log_text, pdf = compile_once(main_path, work)
        parsed = parse_log(log_text, main_path.name)
        passes = 2
    fatal = [item for item in parsed if item.get("line")]
    if code == 127:
        status, reason = "undetermined", "pdflatex is not available; hygiene still ran"
    elif code != 0:
        status, reason = "partial", "compile failed; errors are mapped to file and line where the log provides them"
    elif issues:
        status, reason = "partial", "compile finished; label or citation hygiene still reports issues"
    else:
        status, reason = "success", "pdflatex finished and figure/table labels resolve"
    result = base_result(case_id_of(case), status, reason)
    result.update(
        {
            "main_file": main_path.name,
            "compile": {
                "engine": "pdflatex",
                "passes": passes,
                "exit_code": code,
                "pdf": str(pdf) if pdf else "",
            },
            "errors": parsed,
            "hygiene": issues,
            "artifacts": {"log_tail": "\n".join(log_text.splitlines()[-40:]), "pdf_written": bool(pdf)},
        }
    )
    result["sources"] = [{"source_id": "tex", "path": str(main_path), "locator": main_path.name, "quote": ""}]
    for error in fatal:
        result["uncertainty"].append(
            {"item": f"{error['file']}:{error['line']}", "reason": error["message"], "needs_human": True}
        )
    for issue in issues:
        result["uncertainty"].append(
            {"item": issue.get("label") or issue["kind"], "reason": issue["message"], "needs_human": issue["kind"] != "uncited_float"}
        )
    if status != "success":
        result["limits"] = [reason]
    result["change_records"].append(
        {
            "id": "tex-1",
            "action": "compile",
            "before": main_path.name,
            "after": f"exit {code}; {len(fatal)} line-mapped errors; {len(issues)} hygiene notes",
            "reason": "a TeX error is only actionable with a file and a line",
        }
    )
    Path(args.work).mkdir(parents=True, exist_ok=True)
    write_json(Path(args.output), result)
    print(f"status={status} exit={code} hygiene={len(issues)} errors={len(fatal)}")
    return 0


def empty() -> dict[str, Any]:
    return {"main_file": "", "compile": {}, "errors": [], "hygiene": [], "artifacts": {}}


if __name__ == "__main__":
    raise SystemExit(main())
