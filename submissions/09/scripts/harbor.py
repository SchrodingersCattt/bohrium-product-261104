#!/usr/bin/env python3
"""Result envelope helpers. Standard library only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ENVELOPE = (
    "case_id",
    "status",
    "status_reason",
    "sources",
    "uncertainty",
    "change_records",
)
STATUSES = {"success", "partial", "undetermined", "refused"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def case_id_of(case: dict[str, Any]) -> str:
    for key in ("case_id", "id", "caseId"):
        value = case.get(key)
        if value:
            return str(value)
    return "unknown"


def contract_fields(case: dict[str, Any] | None, defaults: list[str]) -> list[str]:
    fields = list(defaults)
    if not case:
        return fields
    raw = case.get("output_contract")
    extra: list[str] = []
    if isinstance(raw, list):
        extra = [str(item) for item in raw]
    elif isinstance(raw, dict):
        if isinstance(raw.get("fields"), list):
            extra = [str(item) for item in raw["fields"]]
        elif isinstance(raw.get("required"), list):
            extra = [str(item) for item in raw["required"]]
    for item in extra:
        if item not in fields and item not in ENVELOPE:
            fields.append(item)
    return fields


def validate(payload: dict[str, Any], required: list[str]) -> list[str]:
    errors: list[str] = []
    for key in list(ENVELOPE) + list(required):
        if key not in payload:
            errors.append(f"missing field: {key}")
    status = payload.get("status")
    if status not in STATUSES:
        errors.append("status must be success, partial, undetermined, or refused")
    for key in ("sources", "uncertainty", "change_records"):
        if key in payload and not isinstance(payload[key], list):
            errors.append(f"{key} must be a list")
    if status in {"partial", "undetermined", "refused"}:
        if not payload.get("uncertainty") and not payload.get("limits"):
            errors.append(f"{status} needs uncertainty or limits")
    return errors


def base_result(case_id: str, status: str, reason: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": status,
        "status_reason": reason,
        "sources": [],
        "uncertainty": [],
        "change_records": [],
        "limits": [],
    }
