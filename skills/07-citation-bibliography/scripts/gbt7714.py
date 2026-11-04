#!/usr/bin/env python3
"""Simplified numeric reference lines.

This is an original profile with GB/T 7714-style type tags. It is not a
certified GB/T 7714-2015 renderer. doc-forge only supplies plain and markdown.
"""

from __future__ import annotations

import re
from typing import Any

TYPE_TAG = {
    "article": "J",
    "book": "M",
    "inproceedings": "C",
    "incollection": "C",
    "proceedings": "C",
    "thesis": "D",
    "phdthesis": "D",
    "mastersthesis": "D",
    "misc": "Z",
    "online": "EB/OL",
}


def norm_doi(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"(?i)^https?://(dx\.)?doi\.org/", "", text)
    text = re.sub(r"(?i)^doi:\s*", "", text)
    return text


def _people(author: str) -> str:
    people = [part.strip() for part in re.split(r"\s+and\s+", author) if part.strip()]
    if not people:
        return "Anon"
    if len(people) > 3:
        return ", ".join(people[:3]) + ", et al"
    return ", ".join(people)


def format_gbt(entry: Any, entry_type: str) -> str:
    tag = TYPE_TAG.get(entry_type.lower(), "Z")
    author = str(entry.get("author") or entry.get("authors") or "")
    title = str(entry.get("title") or "").strip().rstrip(".")
    year = str(entry.get("year") or "").strip()
    venue = str(entry.get("journal") or entry.get("booktitle") or entry.get("publisher") or "").strip()
    volume = str(entry.get("volume") or "").strip()
    pages = str(entry.get("pages") or "").replace("--", "-").replace("–", "-").strip()
    body = f"{_people(author)}. {title}[{tag}]" if title else f"{_people(author)}[{tag}]"
    if venue:
        body += f". {venue}"
        if year:
            body += f", {year}"
        if volume:
            body += f", {volume}"
        if pages:
            body += f": {pages}"
    elif year:
        body += f". {year}"
    doi = norm_doi(entry.get("doi"))
    if doi:
        body += f". DOI:{doi}"
    if not body.endswith("."):
        body += "."
    return body
