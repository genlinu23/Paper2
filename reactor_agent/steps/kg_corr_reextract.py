from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

from . import kg
from .kg_normalize import normalize_kg


DEFAULT_STEP1_DIR = Path(r"C:\Users\logan\reactor_agent\outputs\step1_run_ready_v1_full")
DEFAULT_BASE_KG_DIR = Path(r"C:\Users\logan\reactor_agent\outputs\step2_causal_kg_run_ready_v2_normalized")
DEFAULT_OUT_DIR = Path(r"C:\Users\logan\reactor_agent\outputs\step2_causal_kg_run_ready_v3_corr_edges")
DEFAULT_FILTERED_CORE = Path(r"C:\Users\logan\reactor_agent\outputs\step2_causal_kg_run_ready_v3_corr_edges_filtered_core.json")

POSITIVE_PATTERNS = [
    r"\bCORR\b",
    r"eCORR",
    r"CO electroreduction",
    r"CO electrolysis",
    r"CO reduction reaction",
    r"electrochemical CO reduction",
    r"CO reduction products",
    r"CO reduction at",
    r"CO reduction",
    r"CO-to-",
    r"CO gas feed",
    r"CO feed",
    r"CO atmosphere",
    r"CO-saturated",
    r"humidified CO",
    r"CO gas was supplied",
    r"CO was fed",
    r"CO feed was",
    r"CO gas feed",
    r"CO was flowed",
    r"CO gas was flowed",
    r"CO partial pressure",
    r"CO coverage",
    r"CO mass transport",
]
NEGATIVE_PATTERNS = [
    r"CO2RR",
    r"CO2 reduction",
    r"carbon dioxide",
    r"cobalt",
]
ELECTROCHEMICAL_CONTEXT = [
    r"electrolyzer",
    r"electrolysis",
    r"electrochemical",
    r"flow cell",
    r"GDE",
    r"gas diffusion electrode",
    r"MEA",
    r"cathode",
    r"anode",
    r"cell",
    r"electrode",
]
DIRECT_CORR_PATTERNS = [
    r"\bCORR\b",
    r"eCORR",
    r"CO electroreduction",
    r"CO electrolysis",
    r"CO reduction reaction",
    r"electrochemical CO reduction",
    r"carbon monoxide reduction",
    r"CO reduction products",
    r"CO reduction at",
]


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _blob_for_row(row: dict) -> str:
    pieces: list[str] = []
    for key in ("structure", "reaction", "membrane", "feed", "performance", "failure"):
        for item in row.get(key, []) or []:
            if isinstance(item, dict):
                pieces.append(str(item.get("value", "")))
            else:
                pieces.append(str(item))
    return " ".join(pieces).lower()


def select_corr_docs(paper_facts: list[dict]) -> tuple[list[str], dict]:
    selected: list[str] = []
    reasons: list[dict] = []
    for row in paper_facts:
        blob = _blob_for_row(row)
        pos_hits = [pattern for pattern in POSITIVE_PATTERNS if re.search(pattern, blob, re.IGNORECASE)]
        direct_hits = [pattern for pattern in DIRECT_CORR_PATTERNS if re.search(pattern, blob, re.IGNORECASE)]
        neg_hits = [pattern for pattern in NEGATIVE_PATTERNS if re.search(pattern, blob, re.IGNORECASE)]
        ctx_hits = [pattern for pattern in ELECTROCHEMICAL_CONTEXT if re.search(pattern, blob, re.IGNORECASE)]
        if not neg_hits and ctx_hits and (direct_hits or (pos_hits and any(term in blob for term in ("co reduction", "faradaic efficiency", "c2+", "mass transport", "coverage", "product")))):
            selected.append(row["doc_id"])
            reasons.append(
                {
                    "doc_id": row["doc_id"],
                    "doi": row.get("doi"),
                    "pos_hits": pos_hits,
                    "direct_hits": direct_hits,
                    "context_hits": ctx_hits,
                    "neg_hits": neg_hits,
                }
            )
    report = {
        "selected_docs": len(selected),
        "selected_doc_ids": selected,
        "reasons": reasons,
        "positive_patterns": POSITIVE_PATTERNS,
        "direct_corr_patterns": DIRECT_CORR_PATTERNS,
        "negative_patterns": NEGATIVE_PATTERNS,
        "electrochemical_context_patterns": ELECTROCHEMICAL_CONTEXT,
    }
    return selected, report


def _merge_kg_payloads(base_nodes: list[dict], base_edges: list[dict], corr_nodes: list[dict], corr_edges: list[dict]) -> tuple[list[dict], list[dict]]:
    nodes: dict[str, dict] = {}
    for node in base_nodes + corr_nodes:
        nodes.setdefault(node["node_id"], dict(node))
    edges: dict[tuple, dict] = {}
    for edge in base_edges + corr_edges:
        key = (edge.get("src"), edge.get("dst"), edge.get("relation"), edge.get("source_doc_id"), edge.get("source_chunk_id"), edge.get("experiment_ref"))
        edges.setdefault(key, dict(edge))
    return list(nodes.values()), list(edges.values())


def build_corr_kg(
    step1_dir: str | Path = DEFAULT_STEP1_DIR,
    base_kg_dir: str | Path = DEFAULT_BASE_KG_DIR,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    filtered_core_path: str | Path = DEFAULT_FILTERED_CORE,
    concurrency: int = 12,
    max_retries: int = 3,
    retry_sleep_s: float = 5.0,
) -> dict:
    step1_path = Path(step1_dir)
    base_path = Path(base_kg_dir)
    out_path = Path(out_dir)
    filtered_core = Path(filtered_core_path)
    paper_facts = _read_json(step1_path / "paper_facts.json")
    core_papers = _read_json(step1_path / "core_papers.json")
    if not isinstance(paper_facts, list) or not isinstance(core_papers, list):
        raise ValueError("paper_facts.json and core_papers.json must be JSON lists")

    selected_docs, filter_report = select_corr_docs(paper_facts)
    if not selected_docs:
        raise ValueError("no CORR docs selected from Step1 corpus")
    _write_json(filtered_core, [{"doc_id": doc_id} for doc_id in selected_docs])

    core_by_doc = {row["doc_id"]: row for row in core_papers}
    selected_core = [core_by_doc[doc_id] for doc_id in selected_docs if doc_id in core_by_doc]
    if not selected_core:
        raise ValueError("selected CORR docs were not found in core_papers.json")

    with TemporaryDirectory(prefix="corr_reextract_") as tmp:
        tmp_dir = Path(tmp)
        raw_corr_dir = tmp_dir / "corr_raw_kg"
        raw_summary = kg.build_kg(
            step1_path,
            filtered_core,
            raw_corr_dir,
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
        corr_nodes = _read_json(raw_corr_dir / "kg_nodes.json")
        corr_edges = _read_json(raw_corr_dir / "kg_edges.json")
        merged_nodes, merged_edges = _merge_kg_payloads(base_nodes, base_edges, corr_nodes, corr_edges)

        merged_raw_dir = tmp_dir / "merged_raw"
        _write_json(merged_raw_dir / "kg_nodes.json", merged_nodes)
        _write_json(merged_raw_dir / "kg_edges.json", merged_edges)
        normalized_summary = normalize_kg(merged_raw_dir, out_path, visualize=False)

    report = {
        "step1_dir": str(step1_path),
        "base_kg_dir": str(base_path),
        "out_dir": str(out_path),
        "filtered_core": str(filtered_core),
        "selected_docs": len(selected_docs),
        "selected_doc_ids": selected_docs,
        "base_nodes": len(base_nodes),
        "base_edges": len(base_edges),
        "corr_raw_nodes": raw_summary["nodes"],
        "corr_raw_edges": raw_summary["edges"],
        "merged_raw_nodes": len(merged_nodes),
        "merged_raw_edges": len(merged_edges),
        "normalized_nodes": normalized_summary["nodes"],
        "normalized_edges": normalized_summary["edges"],
        "normalization": normalized_summary["normalization"],
        "filter_report": filter_report,
    }
    _write_json(out_path / "corr_reextract_report.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Re-extract CORR causal edges from existing Step1 corpus and merge into a normalized KG.")
    parser.add_argument("--step1-dir", default=str(DEFAULT_STEP1_DIR))
    parser.add_argument("--base-kg-dir", default=str(DEFAULT_BASE_KG_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--filtered-core-path", default=str(DEFAULT_FILTERED_CORE))
    parser.add_argument("--concurrency", type=int, default=12)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--retry-sleep-s", type=float, default=5.0)
    args = parser.parse_args()
    report = build_corr_kg(
        step1_dir=args.step1_dir,
        base_kg_dir=args.base_kg_dir,
        out_dir=args.out_dir,
        filtered_core_path=args.filtered_core_path,
        concurrency=args.concurrency,
        max_retries=args.max_retries,
        retry_sleep_s=args.retry_sleep_s,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
