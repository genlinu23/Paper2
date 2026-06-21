from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from . import kg
from .kg_visualize import build_visualizations


DEFAULT_KG_DIR = Path(r"C:\Users\logan\reactor_agent\outputs\step2_causal_kg_run_ready_v1")
DEFAULT_OUT_DIR = Path(r"C:\Users\logan\reactor_agent\outputs\step2_causal_kg_run_ready_v2_normalized")
DEFAULT_SYNONYM_MAP = Path(__file__).resolve().parents[1] / "config" / "synonym_map.json"


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _props_dict(props: object) -> dict[str, Any]:
    if isinstance(props, dict):
        return dict(props)
    if isinstance(props, list):
        result: dict[str, Any] = {}
        for item in props:
            if isinstance(item, dict) and item.get("key"):
                result[str(item["key"])] = item.get("value")
        return result
    return {}


def _norm_text(value: object) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").replace("-", " ").split())


def _node_alias_keys(node: dict) -> set[str]:
    return {
        str(node.get("node_id") or ""),
        _norm_text(node.get("node_id")),
        _norm_text(node.get("label")),
    }


def _load_groups(path: Path) -> list[dict]:
    payload = _read_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("groups"), list):
        raise ValueError(f"synonym map must contain a groups list: {path}")
    return payload["groups"]


def _group_alias_keys(group: dict) -> set[str]:
    aliases = [group["canonical_node_id"], group.get("canonical_label", ""), *group.get("aliases", [])]
    keys: set[str] = set()
    for alias in aliases:
        keys.add(str(alias))
        keys.add(_norm_text(alias))
    return {key for key in keys if key}


def _incident_counts(edges: list[dict]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for edge in edges:
        counts[str(edge["src"])] += 1
        counts[str(edge["dst"])] += 1
    return counts


def _richness(node: dict, incident: Counter[str]) -> tuple[int, int, int]:
    props = _props_dict(node.get("props"))
    return (incident.get(str(node.get("node_id")), 0), len(props), len(str(node.get("label") or "")))


def _merge_props(members: list[dict], group: dict, incident: Counter[str]) -> dict[str, Any]:
    richest = max(members, key=lambda node: _richness(node, incident)) if members else {}
    props = _props_dict(richest.get("props"))
    for node in members:
        for key, value in _props_dict(node.get("props")).items():
            props.setdefault(key, value)
    props["synonym_group"] = group.get("name") or group["canonical_node_id"]
    props["synonym_members"] = sorted({str(node["node_id"]) for node in members})
    props["normalization_method"] = "type_scoped_synonym_map"
    return props


def _edge_key(edge: dict) -> tuple:
    return (
        edge.get("src"),
        edge.get("dst"),
        edge.get("relation"),
        edge.get("source_doc_id"),
        edge.get("source_chunk_id"),
        edge.get("experiment_ref"),
    )


def _normalize_nodes(nodes: list[dict], edges: list[dict], groups: list[dict]) -> tuple[list[dict], dict[str, str], list[dict]]:
    node_by_id = {node["node_id"]: dict(node) for node in nodes}
    incident = _incident_counts(edges)
    redirects: dict[str, str] = {}
    reports: list[dict] = []

    for group in groups:
        node_type = group["type"]
        canonical_id = group["canonical_node_id"]
        alias_keys = _group_alias_keys(group)
        members = [
            node
            for node in nodes
            if node.get("type") == node_type and _node_alias_keys(node) & alias_keys
        ]
        if not members:
            continue

        canonical_node = {
            "node_id": canonical_id,
            "type": node_type,
            "label": group.get("canonical_label") or canonical_id.split(":", 1)[-1].replace("_", " "),
            "props": _merge_props(members, group, incident),
        }
        for member in members:
            redirects[member["node_id"]] = canonical_id
            node_by_id.pop(member["node_id"], None)
        node_by_id[canonical_id] = canonical_node
        reports.append(
            {
                "group": group.get("name") or canonical_id,
                "type": node_type,
                "canonical_node_id": canonical_id,
                "canonical_label": canonical_node["label"],
                "members": sorted(member["node_id"] for member in members),
                "member_incident_edges_before": {member["node_id"]: incident.get(member["node_id"], 0) for member in members},
            }
        )

    return list(node_by_id.values()), redirects, reports


def _normalize_edges(edges: list[dict], redirects: dict[str, str]) -> tuple[list[dict], int]:
    deduped: dict[tuple, dict] = {}
    duplicate_count = 0
    for edge in edges:
        new_edge = dict(edge)
        new_edge["src"] = redirects.get(new_edge["src"], new_edge["src"])
        new_edge["dst"] = redirects.get(new_edge["dst"], new_edge["dst"])
        key = _edge_key(new_edge)
        if key in deduped:
            duplicate_count += 1
            continue
        deduped[key] = new_edge
    return list(deduped.values()), duplicate_count


def _write_outputs(out_dir: Path, nodes: list[dict], edges: list[dict], report: dict, visualize: bool, viz_max_full: int) -> dict:
    node_rows = sorted(nodes, key=lambda row: (row["type"], row["node_id"]))
    edge_rows = sorted(edges, key=lambda row: (row["relation"], row["src"], row["dst"], row.get("source_chunk_id") or ""))
    problems = kg.validate_kg(node_rows, edge_rows)
    if problems:
        raise ValueError("normalized KG validation failed:\n" + "\n".join(problems[:20]))

    _write_json(out_dir / "kg_nodes.json", node_rows)
    _write_json(out_dir / "kg_edges.json", edge_rows)
    kg._write_csv(
        out_dir / "kg_nodes.csv",
        [
            {
                "node_id": row["node_id"],
                "type": row["type"],
                "label": row["label"],
                "props": kg._dict_to_props_json(row.get("props")),
            }
            for row in node_rows
        ],
        ["node_id", "type", "label", "props"],
    )
    kg._write_csv(
        out_dir / "kg_edges.csv",
        edge_rows,
        ["src", "dst", "relation", "source_doc_id", "source_chunk_id", "experiment_ref"],
    )
    kg._write_relation_definitions(out_dir)

    summary = {
        "nodes": len(node_rows),
        "edges": len(edge_rows),
        "node_types": dict(Counter(node["type"] for node in node_rows)),
        "relations": dict(Counter(edge["relation"] for edge in edge_rows)),
        "traceable_edges": sum(1 for edge in edge_rows if kg._edge_traceable(edge)),
        "normalization": report,
    }
    _write_json(out_dir / "kg_summary.json", summary)
    _write_json(out_dir / "normalization_report.json", report)
    _write_json(out_dir / "failures.json", [])
    _write_json(out_dir / "discarded_edges.json", [])
    _write_report_md(out_dir / "NORMALIZATION_REPORT.md", report, summary)
    kg.export_kg_view(out_dir, out_dir)
    if visualize:
        summary["visualization"] = build_visualizations(out_dir, out_dir / "viz", max_full=viz_max_full, cache_lib=False)
        _write_json(out_dir / "kg_summary.json", summary)
    return summary


def _write_report_md(path: Path, report: dict, summary: dict) -> None:
    lines = [
        "# Step2 KG Normalization Report",
        "",
        f"- Input KG: `{report['input_kg_dir']}`",
        f"- Output KG: `{report['output_kg_dir']}`",
        f"- Synonym map: `{report['synonym_map']}`",
        f"- Nodes: {report['input_nodes']} -> {summary['nodes']}",
        f"- Edges: {report['input_edges']} -> {summary['edges']}",
        f"- Deduped redirected edges: {report['deduped_edges']}",
        f"- Traceable edges: {summary['traceable_edges']} / {summary['edges']}",
        "",
        "## Groups",
        "",
    ]
    for group in report["groups"]:
        lines.extend(
            [
                f"### {group['group']}",
                "",
                f"- Type: `{group['type']}`",
                f"- Canonical: `{group['canonical_node_id']}`",
                f"- Members merged: {len(group['members'])}",
                f"- Incident edges before: `{json.dumps(group['member_incident_edges_before'], ensure_ascii=False)}`",
                "",
            ]
        )
        for member in group["members"]:
            lines.append(f"- `{member}`")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def normalize_kg(
    kg_dir: str | Path = DEFAULT_KG_DIR,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    synonym_map: str | Path = DEFAULT_SYNONYM_MAP,
    visualize: bool = False,
    viz_max_full: int = 400,
) -> dict:
    kg_path = Path(kg_dir)
    out_path = Path(out_dir)
    map_path = Path(synonym_map)
    nodes = _read_json(kg_path / "kg_nodes.json")
    edges = _read_json(kg_path / "kg_edges.json")
    groups = _load_groups(map_path)
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("kg_nodes.json and kg_edges.json must be JSON lists")

    normalized_nodes, redirects, group_reports = _normalize_nodes(nodes, edges, groups)
    normalized_edges, deduped_edges = _normalize_edges(edges, redirects)
    report = {
        "input_kg_dir": str(kg_path),
        "output_kg_dir": str(out_path),
        "synonym_map": str(map_path),
        "input_nodes": len(nodes),
        "input_edges": len(edges),
        "redirected_node_ids": len(redirects),
        "deduped_edges": deduped_edges,
        "groups": group_reports,
    }
    return _write_outputs(out_path, normalized_nodes, normalized_edges, report, visualize, viz_max_full)


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize synonym nodes in an existing Step2 KG without re-extraction.")
    parser.add_argument("--kg-dir", default=str(DEFAULT_KG_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--synonym-map", default=str(DEFAULT_SYNONYM_MAP))
    parser.add_argument("--skip-viz", action="store_true")
    parser.add_argument("--viz-max-full", type=int, default=400)
    args = parser.parse_args()
    summary = normalize_kg(
        kg_dir=args.kg_dir,
        out_dir=args.out_dir,
        synonym_map=args.synonym_map,
        visualize=not args.skip_viz,
        viz_max_full=args.viz_max_full,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
