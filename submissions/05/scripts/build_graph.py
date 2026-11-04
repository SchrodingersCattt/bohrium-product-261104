#!/usr/bin/env python3
"""Ground, merge, and query a two-paper graph. Co-occurrence is not an edge."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harbor import base_result, case_id_of, load_json, write_json

ALIAS_RE = re.compile(
    r"([A-Z][A-Za-z0-9\-]+(?:\s+[A-Z][A-Za-z0-9\-]+){0,4})\s+\(([A-Z][A-Za-z0-9\-]{1,16})\)"
)
RELATIONS = {
    "uses",
    "evaluated_on",
    "trained_on",
    "reports",
    "outperforms",
    "underperforms",
    "compares",
    "supports",
    "contradicts",
    "part_of",
    "implemented_with",
    "measures",
    "proposes",
}


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


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.casefold()))


def jaccard(left: str, right: str) -> float:
    a, b = tokens(left), tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def paragraphs_of(payload: dict[str, Any], source_id: str) -> list[dict[str, Any]]:
    rows = []
    for item in payload.get("paragraphs") or []:
        rows.append(
            {
                "source_id": source_id,
                "paragraph_id": str(item.get("paragraph_id")),
                "section": item.get("section") or "",
                "text": str(item.get("text") or ""),
            }
        )
    return rows


def harvest(paragraphs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    found = []
    for paragraph in paragraphs:
        for match in ALIAS_RE.finditer(paragraph["text"]):
            long_form, abbr = squash(match.group(1)), match.group(2)
            if long_form.casefold() not in paragraph["text"].casefold():
                continue
            found.append(
                {
                    "surface": long_form,
                    "aliases": [abbr],
                    "type": "untyped",
                    "source_id": paragraph["source_id"],
                    "paragraph_id": paragraph["paragraph_id"],
                    "evidence": match.group(0),
                    "attributes": {},
                    "origin": "abbreviation",
                }
            )
    return found


def in_paragraph(surface: str, text: str) -> bool:
    if re.search(r"[A-Za-z]", surface):
        return re.search(rf"(?<!\w){re.escape(surface)}(?!\w)", text) is not None
    return surface in text


def ground_candidates(
    candidates: dict[str, Any], paragraphs: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    index = {(row["source_id"], row["paragraph_id"]): row for row in paragraphs}
    nodes = []
    edges = []
    rejected = []
    for node in candidates.get("nodes") or []:
        key = (node.get("source_id"), str(node.get("paragraph_id")))
        paragraph = index.get(key)
        surface = str(node.get("surface") or "")
        if paragraph is None or not surface or not in_paragraph(surface, paragraph["text"]):
            rejected.append({"kind": "node", "id": node.get("local_id"), "reason": "surface is not in the cited paragraph"})
            continue
        nodes.append(
            {
                "local_id": str(node.get("local_id")),
                "surface": surface,
                "aliases": [str(alias) for alias in node.get("aliases") or []],
                "type": str(node.get("type") or "untyped"),
                "source_id": paragraph["source_id"],
                "paragraph_id": paragraph["paragraph_id"],
                "evidence": str(node.get("evidence") or surface),
                "attributes": dict(node.get("attributes") or {}),
                "origin": "candidate",
            }
        )
        if squash(nodes[-1]["evidence"]) not in squash(paragraph["text"]):
            rejected.append({"kind": "node", "id": node.get("local_id"), "reason": "evidence quote is not in the paragraph"})
            nodes.pop()
    kept_ids = {node["local_id"] for node in nodes}
    for edge in candidates.get("edges") or []:
        if edge.get("source_local") not in kept_ids or edge.get("target_local") not in kept_ids:
            rejected.append({"kind": "edge", "id": edge.get("local_id"), "reason": "endpoint was rejected or missing"})
            continue
        relation = str(edge.get("relation") or "")
        if relation not in RELATIONS:
            rejected.append({"kind": "edge", "id": edge.get("local_id"), "reason": f"relation not allowed: {relation}"})
            continue
        key = (edge.get("source_id"), str(edge.get("paragraph_id")))
        paragraph = index.get(key)
        quote = str(edge.get("evidence") or "")
        if paragraph is None or squash(quote) not in squash(paragraph["text"]):
            rejected.append({"kind": "edge", "id": edge.get("local_id"), "reason": "edge evidence is not in the cited paragraph"})
            continue
        edges.append(
            {
                "local_id": str(edge.get("local_id") or f"e{len(edges)+1}"),
                "source_local": edge["source_local"],
                "target_local": edge["target_local"],
                "relation": relation,
                "source_id": paragraph["source_id"],
                "paragraph_id": paragraph["paragraph_id"],
                "evidence": quote,
                "conditions": edge.get("conditions") or "",
            }
        )
    return nodes, edges, rejected


def conflict_values(left: dict[str, Any], right: dict[str, Any]) -> bool:
    keys = set(left.get("attributes") or {}) & set(right.get("attributes") or {})
    for key in keys:
        if left["attributes"][key] != right["attributes"][key]:
            return True
    return False


def same_alias(left: dict[str, Any], right: dict[str, Any]) -> bool:
    names = {left["surface"].casefold(), *(alias.casefold() for alias in left.get("aliases") or [])}
    other = {right["surface"].casefold(), *(alias.casefold() for alias in right.get("aliases") or [])}
    return bool(names & other)


def can_merge(left: dict[str, Any], right: dict[str, Any]) -> str:
    if left["type"] != right["type"] and "untyped" not in {left["type"], right["type"]}:
        return ""
    if conflict_values(left, right):
        return ""
    if left["source_id"] == right["source_id"] and same_alias(left, right):
        return "same paper alias"
    if same_alias(left, right) and jaccard(left["surface"], right["surface"]) >= 0.8:
        return "shared alias and long-form overlap across papers"
    shared = {alias.casefold() for alias in left.get("aliases") or []} & {alias.casefold() for alias in right.get("aliases") or []}
    if shared and jaccard(left["surface"], right["surface"]) >= 0.8:
        return "abbreviation defined for overlapping long forms"
    return ""


def merge_nodes(nodes: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str], list[dict[str, Any]], list[dict[str, Any]]]:
    parent = {node["local_id"]: node["local_id"] for node in nodes}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    merges = []
    conflicts = []
    for index, left in enumerate(nodes):
        for right in nodes[index + 1 :]:
            reason = can_merge(left, right)
            if reason:
                parent[find(right["local_id"])] = find(left["local_id"])
                merges.append({"kept": left["local_id"], "merged": right["local_id"], "reason": reason})
            elif same_alias(left, right) and conflict_values(left, right):
                conflicts.append(
                    {
                        "left": left["local_id"],
                        "right": right["local_id"],
                        "reason": "same surface but conflicting attributes; not merged",
                    }
                )
    groups: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        groups.setdefault(find(node["local_id"]), []).append(node)
    canonical = []
    local_to_canon = {}
    for index, (root, members) in enumerate(groups.items(), start=1):
        typed = [member["type"] for member in members if member["type"] != "untyped"]
        entity_type = typed[0] if typed else "untyped"
        surfaces = []
        aliases = []
        evidence = []
        for member in members:
            surfaces.append(member["surface"])
            aliases.extend(member.get("aliases") or [])
            evidence.append(
                {
                    "source_id": member["source_id"],
                    "paragraph_id": member["paragraph_id"],
                    "quote": member["evidence"],
                }
            )
            local_to_canon[member["local_id"]] = f"n{index}"
        canonical.append(
            {
                "node_id": f"n{index}",
                "type": entity_type,
                "surface": surfaces[0],
                "aliases": sorted(set(aliases) | set(surfaces[1:])),
                "attributes": next((member["attributes"] for member in members if member.get("attributes")), {}),
                "evidence": evidence,
                "member_ids": [member["local_id"] for member in members],
            }
        )
    return canonical, local_to_canon, merges, conflicts


def build_edges(edges: list[dict[str, Any]], local_to_canon: dict[str, str]) -> list[dict[str, Any]]:
    built = []
    for edge in edges:
        built.append(
            {
                "edge_id": edge["local_id"],
                "source": local_to_canon[edge["source_local"]],
                "target": local_to_canon[edge["target_local"]],
                "relation": edge["relation"],
                "conditions": edge["conditions"],
                "evidence": [
                    {
                        "source_id": edge["source_id"],
                        "paragraph_id": edge["paragraph_id"],
                        "quote": edge["evidence"],
                    }
                ],
            }
        )
    return built


def run_queries(queries: list[dict[str, Any]], nodes: list[dict[str, Any]], edges: list[dict[str, Any]], conflicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    answers = []
    for query in queries:
        kind = query.get("type")
        if kind == "find_surface":
            surface = str(query.get("surface") or "").casefold()
            hits = []
            for node in nodes:
                names = {node["surface"].casefold(), *(alias.casefold() for alias in node.get("aliases") or [])}
                if surface in names:
                    hits.append(node["node_id"])
            answers.append({"query_id": query.get("query_id"), "type": kind, "node_ids": hits, "evidence": [node["evidence"] for node in nodes if node["node_id"] in hits]})
        elif kind == "outgoing":
            surface = str(query.get("surface") or "").casefold()
            starts = []
            for node in nodes:
                names = {node["surface"].casefold(), *(alias.casefold() for alias in node.get("aliases") or [])}
                if surface in names:
                    starts.append(node["node_id"])
            found = [edge for edge in edges if edge["source"] in starts]
            answers.append({"query_id": query.get("query_id"), "type": kind, "edges": found, "note": "no edge" if not found else ""})
        elif kind == "conflicts":
            answers.append({"query_id": query.get("query_id"), "type": kind, "conflicts": conflicts})
        else:
            answers.append({"query_id": query.get("query_id"), "type": kind, "error": "unsupported query type"})
    return answers


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an evidence-bound literature graph")
    parser.add_argument("--case", required=True)
    parser.add_argument("--input-root", default="")
    parser.add_argument("--candidates", default="")
    parser.add_argument("--queries", default="")
    parser.add_argument("--work", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    case_path = Path(args.case)
    case = load_json(case_path)
    roots = [case_path.parent, Path("/input")]
    if args.input_root:
        roots.append(Path(args.input_root))
    agent_roots = [Path(args.work), *roots]
    materials = case.get("materials") if isinstance(case.get("materials"), dict) else {}
    manifest_path = locate(str(materials.get("manifest") or "corpus-manifest.json"), roots)
    primary_path = locate(str(materials.get("primary") or "primary-material.json"), roots)
    secondary_path = locate(str(materials.get("secondary") or "secondary-material.json"), roots)
    if not primary_path or not secondary_path:
        result = base_result(case_id_of(case), "refused", "primary and secondary materials are required")
        result.update({"graph": {"nodes": [], "edges": []}, "merges": [], "conflicts": [], "queries": []})
        result["limits"] = ["missing material"]
        write_json(Path(args.output), result)
        return 0
    manifest = load_json(manifest_path) if manifest_path else {"documents": []}
    primary = load_json(primary_path)
    secondary = load_json(secondary_path)
    primary_id = str(primary.get("source_id") or "primary")
    secondary_id = str(secondary.get("source_id") or "secondary")
    paragraphs = paragraphs_of(primary, primary_id) + paragraphs_of(secondary, secondary_id)
    harvested = harvest(paragraphs)
    for index, node in enumerate(harvested, start=1):
        node["local_id"] = f"h{index}"
    candidate_path = Path(args.candidates) if args.candidates else locate(str(materials.get("candidates") or "candidates.json"), agent_roots)
    if candidate_path is not None and not Path(candidate_path).exists():
        candidate_path = None
    rejected: list[dict[str, Any]] = []
    candidate_nodes: list[dict[str, Any]] = []
    candidate_edges: list[dict[str, Any]] = []
    if candidate_path:
        grounded, candidate_edges, rejected = ground_candidates(load_json(candidate_path), paragraphs)
        candidate_nodes = grounded
    nodes_in = harvested + candidate_nodes
    # Drop harvested nodes that duplicate a grounded candidate in the same paragraph.
    canonical_nodes, local_map, merges, conflicts = merge_nodes(nodes_in)
    edges = build_edges(candidate_edges, local_map)
    query_path = Path(args.queries) if args.queries else locate(str(materials.get("queries") or "queries.json"), agent_roots)
    if query_path is not None and not Path(query_path).exists():
        query_path = None
    queries = load_json(query_path) if query_path else []
    if isinstance(queries, dict):
        queries = queries.get("queries") or []
    answers = run_queries(queries, canonical_nodes, edges, conflicts)
    docs = {str(doc.get("source_id")): doc for doc in manifest.get("documents") or []}
    if not candidate_path:
        status, reason = "partial", "alias nodes were harvested; relations need a grounded candidate file"
    elif len(answers) < 3:
        status, reason = "partial", "fewer than 3 queries were executed"
    else:
        status, reason = "success", "nodes and edges are substring-grounded; conflicting values were not merged"
    result = base_result(case_id_of(case), status, reason)
    result.update(
        {
            "graph": {"nodes": canonical_nodes, "edges": edges},
            "merges": merges,
            "conflicts": conflicts,
            "rejected": rejected,
            "queries": answers,
            "documents": [
                {
                    "source_id": source_id,
                    "doi": (docs.get(source_id) or {}).get("doi"),
                    "title": (docs.get(source_id) or {}).get("title"),
                    "authors": (docs.get(source_id) or {}).get("authors"),
                    "license": (docs.get(source_id) or {}).get("license"),
                    "content_sha256": (docs.get(source_id) or {}).get("content_sha256"),
                }
                for source_id in (primary_id, secondary_id)
            ],
            "position_note": "Locators are organizer paragraph_id values, not PDF page numbers.",
        }
    )
    result["sources"] = [
        {
            "source_id": row["source_id"],
            "path": str(primary_path if row["source_id"] == primary_id else secondary_path),
            "locator": row["paragraph_id"],
            "quote": row["text"][:240],
        }
        for row in paragraphs
    ]
    for item in rejected:
        result["uncertainty"].append({"item": str(item.get("id")), "reason": item["reason"], "needs_human": True})
    for item in conflicts:
        result["uncertainty"].append({"item": f"{item['left']}/{item['right']}", "reason": item["reason"], "needs_human": True})
    if not manifest_path:
        result["uncertainty"].append({"item": "manifest", "reason": "corpus-manifest.json missing; DOI left null", "needs_human": True})
    if status != "success":
        result["limits"] = [reason]
    result["change_records"].append(
        {
            "id": "kg-1",
            "action": "merge-or-keep",
            "before": "per-paper surfaces",
            "after": "merged only when alias and long form agree and attributes do not conflict",
            "reason": "a shared method name is not a shared measurement",
        }
    )
    digest = hashlib.sha256(Path(args.output).as_posix().encode("utf-8")).hexdigest()[:8]
    result["change_records"].append(
        {
            "id": f"kg-run-{digest}",
            "action": "query",
            "before": "",
            "after": f"{len(answers)} queries",
            "reason": "queries are executed on the built graph, not described",
        }
    )
    Path(args.work).mkdir(parents=True, exist_ok=True)
    write_json(Path(args.output), result)
    write_json(Path(args.work) / "graph.json", result["graph"])
    print(f"status={status} nodes={len(canonical_nodes)} edges={len(edges)} queries={len(answers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
