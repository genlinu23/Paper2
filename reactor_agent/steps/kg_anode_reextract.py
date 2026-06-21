from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from . import kg
from .kg_normalize import normalize_kg


DEFAULT_STEP1_DIR = Path(r"C:\Users\logan\reactor_agent\outputs\step1_run_ready_v1_full")
DEFAULT_BASE_KG_DIR = Path(r"C:\Users\logan\reactor_agent\outputs\step2_causal_kg_run_ready_v5_corr_edges")
DEFAULT_OUT_DIR = Path(r"C:\Users\logan\reactor_agent\outputs\step2_causal_kg_v6_anode_edges")
DEFAULT_FILTERED_CORE = Path(r"C:\Users\logan\reactor_agent\outputs\step2_causal_kg_v6_anode_edges_filtered_core.json")

FACT_FIELDS = ("structure", "reaction", "membrane", "feed", "performance", "failure")

HOR_PATTERNS = [
    r"\bHOR\b",
    r"hydrogen oxidation",
    r"hydrogen oxidation reaction",
    r"H2 oxidation",
    r"H2-oxidation",
]

PT_PTL_PATTERNS = [
    r"Pt@PTL",
    r"Pt\s*[-@/]?\s*PTL",
    r"Pt[- ]loaded PTL",
    r"Pt[- ]coated PTL",
    r"Pt.*porous transport layer",
    r"platinum.*porous transport layer",
    r"Pt.*titanium felt",
    r"Pt[- ]RuO2.*PTL",
    r"Pt/RuO2.*PTL",
]

ANODE_CONTEXT_PATTERNS = [
    r"anode",
    r"anodic",
    r"gas-fed anode",
    r"H2 feed",
    r"H2-fed",
    r"hydrogen feed",
    r"hydrogen-fed",
    r"KOH aerosol",
    r"KOH spray",
    r"alkaline aerosol",
    r"paired electrolysis",
    r"paired electrolyzer",
    r"porous transport layer",
    r"\bPTL\b",
]

PROJECT_CONTEXT_PATTERNS = [
    r"\bCORR\b",
    r"CO electroreduction",
    r"CO reduction",
    r"CO electrolysis",
    r"carbon monoxide reduction",
    r"CO2 reduction",
    r"CO2RR",
    r"paired electrolysis",
]

PURE_OER_PATTERNS = [
    r"\bOER\b",
    r"oxygen evolution",
    r"oxygen evolution reaction",
    r"water electrolysis",
    r"water electrolyzer",
    r"PEM electrolyzer",
    r"AEM water electrolyzer",
]

PERFORMANCE_PATTERNS = [
    r"performance",
    r"stability",
    r"stable",
    r"durability",
    r"overpotential",
    r"current density",
    r"cell voltage",
    r"FE\b",
    r"faradaic",
    r"activity",
]

ANODE_RING_PATTERNS = [
    *HOR_PATTERNS,
    *PT_PTL_PATTERNS,
    r"H2 feed",
    r"hydrogen feed",
    r"KOH aerosol",
    r"KOH spray",
    r"gas-fed anode",
    r"paired electrolysis",
]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _print_json(payload: object) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    sys.stdout.buffer.write(text.encode("utf-8"))


def _matches(patterns: list[str], text: str) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text, re.IGNORECASE)]


def _fact_items(row: dict) -> list[dict]:
    items: list[dict] = []
    for field in FACT_FIELDS:
        for fact in row.get(field, []) or []:
            if not isinstance(fact, dict):
                continue
            value = str(fact.get("value") or "")
            if not value or value == "not_mentioned":
                continue
            items.append(
                {
                    "field": field,
                    "value": value,
                    "chunk_id": fact.get("chunk_id"),
                    "section_title": fact.get("section_title"),
                }
            )
    return items


def _blob_for_row(row: dict) -> str:
    return " ".join(item["value"] for item in _fact_items(row))


def _hit_examples(row: dict, patterns: list[str], limit: int = 8) -> list[dict]:
    examples: list[dict] = []
    for item in _fact_items(row):
        hits = _matches(patterns, item["value"])
        if not hits:
            continue
        examples.append(
            {
                "field": item["field"],
                "chunk_id": item["chunk_id"],
                "section_title": item["section_title"],
                "patterns": hits,
                "value": item["value"][:700],
            }
        )
        if len(examples) >= limit:
            break
    return examples


def select_anode_docs(paper_facts: list[dict]) -> tuple[list[str], dict]:
    selected: list[str] = []
    reasons: list[dict] = []
    rejected_oer_only: list[dict] = []

    for row in paper_facts:
        items = _fact_items(row)
        blob = " ".join(item["value"] for item in items)
        hor_hits = _matches(HOR_PATTERNS, blob)
        anode_hits = _matches(ANODE_CONTEXT_PATTERNS, blob)
        project_hits = _matches(PROJECT_CONTEXT_PATTERNS, blob)
        oer_hits = _matches(PURE_OER_PATTERNS, blob)
        performance_hits = _matches(PERFORMANCE_PATTERNS, blob)
        pt_ptl_hits: list[str] = []

        item_hit_rows: list[dict] = []
        for item in items:
            text = item["value"]
            item_hor = _matches(HOR_PATTERNS, text)
            item_pt_ptl = _matches(PT_PTL_PATTERNS, text)
            item_anode = _matches(ANODE_CONTEXT_PATTERNS, text)
            item_h2 = _matches([r"\bH2\b", r"hydrogen"], text)
            item_spray = _matches([r"KOH aerosol", r"KOH spray", r"alkaline aerosol"], text)
            item_paired = _matches([r"paired electrolysis", r"paired electrolyzer"], text)
            if item_pt_ptl:
                pt_ptl_hits.extend(item_pt_ptl)
            item_hit_rows.append(
                {
                    "item": item,
                    "hor": item_hor,
                    "pt_ptl": item_pt_ptl,
                    "anode": item_anode,
                    "h2": item_h2,
                    "spray": item_spray,
                    "paired": item_paired,
                }
            )

        has_direct_hor_anode = any(hit["hor"] and hit["anode"] for hit in item_hit_rows)
        has_pt_ptl_anode = any(hit["pt_ptl"] and hit["anode"] for hit in item_hit_rows)
        has_spray_h2_anode = any(hit["spray"] and hit["h2"] and hit["anode"] for hit in item_hit_rows)
        has_paired_h2_anode = any(hit["paired"] and hit["anode"] and (hit["h2"] or hit["hor"]) for hit in item_hit_rows)
        has_cross_fact_hor_anode = bool(
            hor_hits
            and any(hit["anode"] and hit["h2"] for hit in item_hit_rows)
            and any(hit["hor"] for hit in item_hit_rows)
        )
        likely_oer_only = bool(oer_hits and not (hor_hits or has_spray_h2_anode or has_paired_h2_anode or project_hits))

        if likely_oer_only:
            rejected_oer_only.append(
                {
                    "doc_id": row.get("doc_id"),
                    "doi": row.get("doi"),
                    "oer_hits": oer_hits,
                    "examples": _hit_examples(row, PURE_OER_PATTERNS, limit=3),
                }
            )
            continue

        if has_direct_hor_anode or has_pt_ptl_anode or has_spray_h2_anode or has_paired_h2_anode or has_cross_fact_hor_anode:
            selected.append(row["doc_id"])
            reasons.append(
                {
                    "doc_id": row["doc_id"],
                    "doi": row.get("doi"),
                    "selection_flags": {
                        "direct_hor_anode": has_direct_hor_anode,
                        "pt_ptl_anode": has_pt_ptl_anode,
                        "spray_h2_anode": has_spray_h2_anode,
                        "paired_h2_anode": has_paired_h2_anode,
                        "cross_fact_hor_h2_anode": has_cross_fact_hor_anode,
                    },
                    "hor_hits": sorted(set(hor_hits)),
                    "pt_ptl_hits": sorted(set(pt_ptl_hits)),
                    "anode_context_hits": anode_hits,
                    "project_context_hits": project_hits,
                    "performance_hits": performance_hits,
                    "oer_noise_hits": oer_hits,
                    "examples": _hit_examples(row, ANODE_RING_PATTERNS + PERFORMANCE_PATTERNS, limit=10),
                }
            )

    report = {
        "selected_docs": len(selected),
        "selected_doc_ids": selected,
        "reasons": reasons,
        "rejected_oer_only_docs": len(rejected_oer_only),
        "rejected_oer_only_samples": rejected_oer_only[:25],
        "patterns": {
            "hor": HOR_PATTERNS,
            "pt_ptl": PT_PTL_PATTERNS,
            "anode_context": ANODE_CONTEXT_PATTERNS,
            "project_context": PROJECT_CONTEXT_PATTERNS,
            "pure_oer": PURE_OER_PATTERNS,
            "performance": PERFORMANCE_PATTERNS,
        },
    }
    return selected, report


def _merge_kg_payloads(
    base_nodes: list[dict],
    base_edges: list[dict],
    anode_nodes: list[dict],
    anode_edges: list[dict],
) -> tuple[list[dict], list[dict]]:
    nodes: dict[str, dict] = {}
    for node in base_nodes + anode_nodes:
        nodes.setdefault(node["node_id"], dict(node))

    edges: dict[tuple, dict] = {}
    for edge in base_edges + anode_edges:
        key = (
            edge.get("src"),
            edge.get("dst"),
            edge.get("relation"),
            edge.get("source_doc_id"),
            edge.get("source_chunk_id"),
            edge.get("experiment_ref"),
        )
        edges.setdefault(key, dict(edge))
    return list(nodes.values()), list(edges.values())


def _edge_key(edge: dict) -> tuple:
    return (
        edge.get("src"),
        edge.get("dst"),
        edge.get("relation"),
        edge.get("source_doc_id"),
        edge.get("source_chunk_id"),
        edge.get("experiment_ref"),
    )


def _node_text(node: dict) -> str:
    props = node.get("props")
    if isinstance(props, dict):
        prop_text = " ".join(str(value) for value in props.values())
    else:
        prop_text = str(props or "")
    return f"{node.get('node_id', '')} {node.get('type', '')} {node.get('label', '')} {prop_text}".lower()


def _edge_text(edge: dict, node_by_id: dict[str, dict]) -> str:
    src = node_by_id.get(edge.get("src"), {})
    dst = node_by_id.get(edge.get("dst"), {})
    return f"{edge.get('relation', '')} {_node_text(src)} {_node_text(dst)}".lower()


def _edge_touches_anode_ring(edge: dict, node_by_id: dict[str, dict]) -> bool:
    text = _edge_text(edge, node_by_id)
    has_anode_side = any(term in text for term in ("anode", "ptl", "porous transport layer", "platinum", " pt", "pt@", "h2", "hydrogen", "koh aerosol", "koh spray"))
    has_target = any(term in text for term in ("hor", "hydrogen oxidation", "h2 oxidation", "ptl", "koh aerosol", "koh spray", "performance", "stability", "overpotential", "current density", "cell voltage"))
    return has_anode_side and has_target


def _analyze_edges(base_edges: list[dict], out_nodes: list[dict], out_edges: list[dict]) -> dict:
    base_keys = {_edge_key(edge) for edge in base_edges}
    new_edges = [edge for edge in out_edges if _edge_key(edge) not in base_keys]
    node_by_id = {node["node_id"]: node for node in out_nodes}
    anode_ring_edges = [edge for edge in new_edges if _edge_touches_anode_ring(edge, node_by_id)]
    pt_ptl_incident = [
        edge
        for edge in out_edges
        if edge.get("src") == "Anode:Pt_PTL_anode" or edge.get("dst") == "Anode:Pt_PTL_anode"
    ]
    traceable_new = sum(1 for edge in new_edges if kg._edge_traceable(edge))
    return {
        "new_edges_total": len(new_edges),
        "new_traceable_edges": traceable_new,
        "new_relations": dict(Counter(edge.get("relation") for edge in new_edges)),
        "new_anode_ring_edges": len(anode_ring_edges),
        "new_anode_ring_edge_samples": anode_ring_edges[:25],
        "pt_ptl_incident_edges_total": len(pt_ptl_incident),
        "pt_ptl_incident_edge_samples": pt_ptl_incident[:25],
    }


def _write_report_md(path: Path, report: dict) -> None:
    selected = report.get("filter_report", {}).get("selected_docs", 0)
    lines = [
        "# Step2 Local Anode Re-extraction Report",
        "",
        f"- Step1 input: `{report['step1_dir']}`",
        f"- Base KG: `{report['base_kg_dir']}`",
        f"- Output KG: `{report['out_dir']}`",
        f"- Filtered core: `{report['filtered_core']}`",
        f"- Selected HOR/Pt@PTL anode docs: {selected}",
        f"- Mode: `{report.get('mode', 'build')}`",
        "",
        "## Selection Summary",
        "",
        f"- Flag counts: `{json.dumps(report.get('selection_summary', {}).get('flag_counts', {}), ensure_ascii=False)}`",
        f"- Docs with direct Pt@PTL/PTL-anode hits: {report.get('selection_summary', {}).get('docs_with_pt_ptl_direct_hits')}",
        f"- Docs with KOH aerosol/spray + H2 anode hits: {report.get('selection_summary', {}).get('docs_with_koh_aerosol_or_spray_hits')}",
        "",
        "## Extraction Summary",
        "",
    ]
    if report.get("mode") == "dry_run":
        lines.extend(
            [
                "- LLM extraction was not run.",
                "- This report only records which existing Step1 papers match the local anode-ring selector.",
                f"- Blocker: {report.get('blocker') or 'none'}",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"- Base nodes: {report.get('base_nodes')}",
                f"- Base edges: {report.get('base_edges')}",
                f"- Raw anode nodes: {report.get('anode_raw_nodes')}",
                f"- Raw anode edges: {report.get('anode_raw_edges')}",
                f"- Merged raw nodes: {report.get('merged_raw_nodes')}",
                f"- Merged raw edges: {report.get('merged_raw_edges')}",
                f"- Normalized nodes: {report.get('normalized_nodes')}",
                f"- Normalized edges: {report.get('normalized_edges')}",
                "",
                "## New Edge Analysis",
                "",
                f"- New edges total: {report.get('edge_analysis', {}).get('new_edges_total')}",
                f"- New traceable edges: {report.get('edge_analysis', {}).get('new_traceable_edges')}",
                f"- New Pt@PTL/HOR anode-ring edges: {report.get('edge_analysis', {}).get('new_anode_ring_edges')}",
                f"- Canonical `Anode:Pt_PTL_anode` incident edges: {report.get('edge_analysis', {}).get('pt_ptl_incident_edges_total')}",
                "",
            ]
        )

    lines.extend(["## Selected Doc Samples", ""])
    for item in report.get("filter_report", {}).get("reasons", [])[:20]:
        flags = item.get("selection_flags", {})
        lines.append(f"### {item.get('doc_id')} | {item.get('doi') or ''}")
        lines.append("")
        lines.append(f"- Flags: `{json.dumps(flags, ensure_ascii=False)}`")
        lines.append(f"- HOR hits: `{item.get('hor_hits')}`")
        lines.append(f"- Pt/PTL hits: `{item.get('pt_ptl_hits')}`")
        lines.append(f"- Anode context hits: `{item.get('anode_context_hits')}`")
        for example in item.get("examples", [])[:3]:
            value = str(example.get("value", "")).replace("\n", " ")
            lines.append(f"- {example.get('field')} `{example.get('chunk_id')}`: {value}")
        lines.append("")

    _write_text(path, "\n".join(lines).rstrip() + "\n")


def dry_run_anode_selection(
    step1_dir: str | Path = DEFAULT_STEP1_DIR,
    base_kg_dir: str | Path = DEFAULT_BASE_KG_DIR,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    filtered_core_path: str | Path = DEFAULT_FILTERED_CORE,
) -> dict:
    step1_path = Path(step1_dir)
    base_path = Path(base_kg_dir)
    out_path = Path(out_dir)
    filtered_core = Path(filtered_core_path)
    paper_facts = _read_json(step1_path / "paper_facts.json")
    if not isinstance(paper_facts, list):
        raise ValueError("paper_facts.json must be a JSON list")

    selected_docs, filter_report = select_anode_docs(paper_facts)
    flag_counts: Counter[str] = Counter()
    for item in filter_report["reasons"]:
        for key, value in item.get("selection_flags", {}).items():
            if value:
                flag_counts[key] += 1
    _write_json(filtered_core, [{"doc_id": doc_id} for doc_id in selected_docs])
    report = {
        "mode": "dry_run",
        "step1_dir": str(step1_path),
        "base_kg_dir": str(base_path),
        "out_dir": str(out_path),
        "filtered_core": str(filtered_core),
        "selection_summary": {
            "flag_counts": dict(flag_counts),
            "docs_with_pt_ptl_direct_hits": sum(1 for item in filter_report["reasons"] if item.get("pt_ptl_hits")),
            "docs_with_koh_aerosol_or_spray_hits": sum(
                1 for item in filter_report["reasons"] if item.get("selection_flags", {}).get("spray_h2_anode")
            ),
        },
        "filter_report": filter_report,
        "env": {
            "VECTORENGINE_API_KEY": "set" if os.environ.get("VECTORENGINE_API_KEY") else "missing",
            "VECTORENGINE_BASE_URL": os.environ.get("VECTORENGINE_BASE_URL") or "default",
        },
        "blocker": None if os.environ.get("VECTORENGINE_API_KEY") else "Full Step2 LLM re-extraction requires VECTORENGINE_API_KEY in the process environment.",
    }
    _write_json(out_path / "anode_reextract_dry_run_report.json", report)
    _write_report_md(out_path / "ANODE_REEXTRACT_REPORT.md", report)
    return report


def build_anode_kg(
    step1_dir: str | Path = DEFAULT_STEP1_DIR,
    base_kg_dir: str | Path = DEFAULT_BASE_KG_DIR,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    filtered_core_path: str | Path = DEFAULT_FILTERED_CORE,
    concurrency: int = 8,
    max_retries: int = 3,
    retry_sleep_s: float = 5.0,
) -> dict:
    if not os.environ.get("VECTORENGINE_API_KEY"):
        raise RuntimeError("VECTORENGINE_API_KEY is required for Step2 KG re-extraction.")

    step1_path = Path(step1_dir)
    base_path = Path(base_kg_dir)
    out_path = Path(out_dir)
    filtered_core = Path(filtered_core_path)
    if (out_path / "kg_edges.json").exists():
        raise FileExistsError(f"output KG already exists and will not be overwritten: {out_path}")

    paper_facts = _read_json(step1_path / "paper_facts.json")
    core_papers = _read_json(step1_path / "core_papers.json")
    if not isinstance(paper_facts, list) or not isinstance(core_papers, list):
        raise ValueError("paper_facts.json and core_papers.json must be JSON lists")

    selected_docs, filter_report = select_anode_docs(paper_facts)
    if not selected_docs:
        raise ValueError("no HOR/Pt@PTL anode docs selected from Step1 corpus")
    _write_json(filtered_core, [{"doc_id": doc_id} for doc_id in selected_docs])
    flag_counts: Counter[str] = Counter()
    for item in filter_report["reasons"]:
        for key, value in item.get("selection_flags", {}).items():
            if value:
                flag_counts[key] += 1

    core_by_doc = {row["doc_id"]: row for row in core_papers}
    selected_core = [core_by_doc[doc_id] for doc_id in selected_docs if doc_id in core_by_doc]
    if not selected_core:
        raise ValueError("selected anode docs were not found in core_papers.json")

    with TemporaryDirectory(prefix="anode_reextract_") as tmp:
        tmp_dir = Path(tmp)
        raw_anode_dir = tmp_dir / "anode_raw_kg"
        raw_summary = kg.build_kg(
            step1_path,
            filtered_core,
            raw_anode_dir,
            concurrency=concurrency,
            max_retries=max_retries,
            retry_sleep_s=retry_sleep_s,
            overwrite=False,
            limit=None,
            visualize=False,
            viz_cache_lib=False,
        )
        base_nodes = _read_json(base_path / "kg_nodes.json")
        base_edges = _read_json(base_path / "kg_edges.json")
        anode_nodes = _read_json(raw_anode_dir / "kg_nodes.json")
        anode_edges = _read_json(raw_anode_dir / "kg_edges.json")
        merged_nodes, merged_edges = _merge_kg_payloads(base_nodes, base_edges, anode_nodes, anode_edges)

        merged_raw_dir = tmp_dir / "merged_raw"
        _write_json(merged_raw_dir / "kg_nodes.json", merged_nodes)
        _write_json(merged_raw_dir / "kg_edges.json", merged_edges)
        normalized_summary = normalize_kg(merged_raw_dir, out_path, visualize=False)

    out_nodes = _read_json(out_path / "kg_nodes.json")
    out_edges = _read_json(out_path / "kg_edges.json")
    edge_analysis = _analyze_edges(base_edges, out_nodes, out_edges)
    report = {
        "mode": "build",
        "step1_dir": str(step1_path),
        "base_kg_dir": str(base_path),
        "out_dir": str(out_path),
        "filtered_core": str(filtered_core),
        "selected_docs": len(selected_docs),
        "selected_doc_ids": selected_docs,
        "base_nodes": len(base_nodes),
        "base_edges": len(base_edges),
        "anode_raw_nodes": raw_summary["nodes"],
        "anode_raw_edges": raw_summary["edges"],
        "merged_raw_nodes": len(merged_nodes),
        "merged_raw_edges": len(merged_edges),
        "normalized_nodes": normalized_summary["nodes"],
        "normalized_edges": normalized_summary["edges"],
        "normalization": normalized_summary["normalization"],
        "edge_analysis": edge_analysis,
        "selection_summary": {
            "flag_counts": dict(flag_counts),
            "docs_with_pt_ptl_direct_hits": sum(1 for item in filter_report["reasons"] if item.get("pt_ptl_hits")),
            "docs_with_koh_aerosol_or_spray_hits": sum(
                1 for item in filter_report["reasons"] if item.get("selection_flags", {}).get("spray_h2_anode")
            ),
        },
        "filter_report": filter_report,
    }
    _write_json(out_path / "anode_reextract_report.json", report)
    _write_report_md(out_path / "ANODE_REEXTRACT_REPORT.md", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-extract only the Pt@PTL/HOR anode causal ring from the existing Step1 corpus.")
    parser.add_argument("--step1-dir", default=str(DEFAULT_STEP1_DIR))
    parser.add_argument("--base-kg-dir", default=str(DEFAULT_BASE_KG_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--filtered-core-path", default=str(DEFAULT_FILTERED_CORE))
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--retry-sleep-s", type=float, default=5.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        report = dry_run_anode_selection(
            step1_dir=args.step1_dir,
            base_kg_dir=args.base_kg_dir,
            out_dir=args.out_dir,
            filtered_core_path=args.filtered_core_path,
        )
    else:
        report = build_anode_kg(
            step1_dir=args.step1_dir,
            base_kg_dir=args.base_kg_dir,
            out_dir=args.out_dir,
            filtered_core_path=args.filtered_core_path,
            concurrency=args.concurrency,
            max_retries=args.max_retries,
            retry_sleep_s=args.retry_sleep_s,
        )
    _print_json(report)


if __name__ == "__main__":
    main()
