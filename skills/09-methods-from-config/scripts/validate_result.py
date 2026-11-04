#!/usr/bin/env python3
"""Validate result.json against the skill contract and the case output_contract."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harbor import contract_fields, load_json, validate


def unwrap(payload: dict) -> dict:
    if "case_id" not in payload and isinstance(payload.get("result"), dict):
        return payload["result"]
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a skill result.json")
    parser.add_argument("result")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--case", default="")
    args = parser.parse_args()
    payload = unwrap(load_json(Path(args.result)))
    contract = load_json(Path(args.contract))
    case = load_json(Path(args.case)) if args.case else None
    required = contract_fields(case, list(contract.get("required", [])))
    errors = validate(payload, required)
    for key in contract.get("lists", []):
        if key in payload and not isinstance(payload[key], list):
            errors.append(f"{key} must be a list")
    if errors:
        print("\n".join(errors))
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
