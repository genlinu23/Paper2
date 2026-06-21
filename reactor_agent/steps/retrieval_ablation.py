from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from . import reasoning, reasoning_retrieval


DEFAULT_KG_DIR = Path(r"C:\Users\logan\reactor_agent\outputs\step2_causal_kg_run_ready_v1")
DEFAULT_OUT_DIR = Path(r"C:\Users\logan\reactor_agent\outputs\step3_retrieval_ablation")
MAX_EDGES = 80
MMR_POOL_SIZE = 500
MMR_LAMBDA = 0.5
EGO_ANCHORS = 24
EGO_TYPE_QUOTA = 3
EGO_ROLE_TYPE_QUOTA = 6

CORR_TERMS = ("corr", "co reduction", "co electroreduction", "carbon monoxide reduction", "co electrolysis", "co-to-c2+", "co-to-acetate")
CO2RR_TERMS = ("co2rr", "co2 reduction", "carbon dioxide reduction", "co2 feed", "carbon dioxide", "co2")

EVAL_KEYWORDS = {
    "R1": ("corr", "solid electrolyte", "solid-electrolyte", "solid mea", "hor"),
    "R2": ("1 m koh", "koh", "liquid electrolyte", "liquid layer"),
    "R3": ("double-sided gas", "double sided gas", "aem", "hor"),
    "R4": ("water-retention", "water retention", "water retaining", "pre-cation", "pre cation", "cation layer"),
    "R5": ("h2", "spray", "aerosol", "carbon paper", "carbon-paper", " co ", "corr", "co reduction"),
    "R6": ("pt@ptl", "ptl", "h2", "koh aerosol", "aerosol"),
    "R7": ("pt@ptl", "ptl", "porous ptfe", "ptfe", "porous diaphragm", "diaphragm", "cu", "copper", "carbon paper", "carbon-paper"),
}

TOKEN_RE = re.compile(r"[a-z0-9+@-]{2,}")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_kg(kg_dir: Path) -> tuple[list[dict], list[dict], dict[str, dict]]:
    nodes, edges = reasoning._load_kg(kg_dir)
    return nodes, edges, reasoning._nodes_by_id(nodes)


def _node_text(node: dict) -> str:
    return reasoning._node_text(node)


def _edge_text(edge: dict, node_by_id: dict[str, dict]) -> str:
    return reasoning._edge_text(edge, node_by_id)


def _edge_label(edge: dict, node_by_id: dict[str, dict]) -> str:
    return reasoning._edge_label(edge, node_by_id)


def _edge_key(edge: dict) -> tuple:
    return reasoning._edge_key(edge)


def _dedupe_edges(edges: list[dict]) -> list[dict]:
    keyed: dict[tuple, dict] = {}
    for edge in edges:
        keyed.setdefault(_edge_key(edge), edge)
    return list(keyed.values())


def _tokens(text: str) -> Counter[str]:
    return Counter(TOKEN_RE.findall(text.lower()))


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(value * b.get(key, 0) for key, value in a.items())
    if not dot:
        return 0.0
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def _query_text(last_diagnosis: str) -> str:
    terms = reasoning._diagnosis_query_terms(last_diagnosis)
    return " ".join([last_diagnosis, *terms])


def _query_terms(last_diagnosis: str) -> list[str]:
    return reasoning._diagnosis_query_terms(last_diagnosis)


def _anchor_query_terms(last_diagnosis: str) -> list[str]:
    return reasoning_retrieval.anchor_query_terms(_query_terms(last_diagnosis))


def _seed_nodes(nodes: list[dict], query_terms: list[str], types: set[str] | None = None) -> set[str]:
    seeds = set()
    for node in nodes:
        if types is not None and node.get("type") not in types:
            continue
        text = _node_text(node)
        if any(term.lower() in text for term in query_terms):
            seeds.add(node["node_id"])
    return seeds


def _edge_query_hits(edge: dict, node_by_id: dict[str, dict], query_terms: list[str]) -> int:
    text = _edge_text(edge, node_by_id)
    return sum(1 for term in query_terms if term.lower() in text)


def _subgraph(edge_subset: list[dict], node_by_id: dict[str, dict], extra_node_ids: set[str] | None = None) -> dict:
    clean_edges = [{k: v for k, v in edge.items() if not k.startswith("_")} for edge in edge_subset]
    node_ids = {edge["src"] for edge in clean_edges} | {edge["dst"] for edge in clean_edges}
    if extra_node_ids:
        node_ids |= extra_node_ids
    return {
        "nodes": [node_by_id[node_id] for node_id in sorted(node_ids) if node_id in node_by_id],
        "edges": clean_edges,
    }


def _incident_edges(edges: list[dict], seed_ids: set[str]) -> list[dict]:
    incident = reasoning._incident_edges(edges)
    result = []
    for seed_id in seed_ids:
        result.extend(incident.get(seed_id, []))
    return _dedupe_edges(result)


def _algorithm_a(nodes: list[dict], edges: list[dict], node_by_id: dict[str, dict], round_id: str, diagnosis: str) -> tuple[dict, dict]:
    query_terms = _query_terms(diagnosis)
    seed_types = {"Failure Mode", "Diagnosis", "Performance", "Reactor", "Cathode", "Anode", "Separator", "Gas Feed", "Electrolyte", "Operating Condition"}
    seed_ids = _seed_nodes(nodes, query_terms, seed_types)
    candidates = _incident_edges(edges, seed_ids)
    ranked = sorted(
        candidates,
        key=lambda edge: (
            _edge_query_hits(edge, node_by_id, query_terms),
            str(edge.get("relation") or ""),
            str(edge.get("source_doc_id") or ""),
            str(edge.get("src") or ""),
            str(edge.get("dst") or ""),
        ),
        reverse=True,
    )
    return _subgraph(ranked[:MAX_EDGES], node_by_id), {
        "algorithm": "A_keyword_freq",
        "query_terms": query_terms,
        "seed_count": len(seed_ids),
        "candidate_edges": len(candidates),
        "selection": "incident_edges_sorted_by_query_term_hits_top80",
    }


def _mmr_select(edge_vectors: list[Counter[str]], relevance: list[float], pool_indices: list[int], max_edges: int, lambda_: float) -> list[int]:
    selected: list[int] = []
    remaining = set(pool_indices)
    while remaining and len(selected) < max_edges:
        best_idx = None
        best_score = -float("inf")
        for idx in remaining:
            diversity_penalty = 0.0
            if selected:
                diversity_penalty = max(_cosine(edge_vectors[idx], edge_vectors[chosen]) for chosen in selected)
            score = lambda_ * relevance[idx] - (1.0 - lambda_) * diversity_penalty
            if score > best_score:
                best_score = score
                best_idx = idx
        selected.append(best_idx)  # type: ignore[arg-type]
        remaining.remove(best_idx)  # type: ignore[arg-type]
    return selected


def _algorithm_b(nodes: list[dict], edges: list[dict], node_by_id: dict[str, dict], round_id: str, diagnosis: str) -> tuple[dict, dict]:
    query = _tokens(_query_text(diagnosis))
    edge_vectors = [_tokens(_edge_text(edge, node_by_id)) for edge in edges]
    relevance = [_cosine(query, vector) for vector in edge_vectors]
    pool = sorted(range(len(edges)), key=lambda idx: relevance[idx], reverse=True)[: min(MMR_POOL_SIZE, len(edges))]
    selected_indices = _mmr_select(edge_vectors, relevance, pool, MAX_EDGES, MMR_LAMBDA)
    selected_edges = [edges[idx] for idx in selected_indices]
    return _subgraph(selected_edges, node_by_id), {
        "algorithm": "B_mmr",
        "embedding_backend": "local_token_cosine",
        "query_boundary": "diagnosis_plus_neutral_lexical_expansions_only",
        "pool_size": len(pool),
        "candidate_edges": len(edges),
        "mmr_lambda": MMR_LAMBDA,
    }


def _algorithm_c(nodes: list[dict], edges: list[dict], node_by_id: dict[str, dict], round_id: str, diagnosis: str) -> tuple[dict, dict]:
    query_terms = _query_terms(diagnosis)
    scored_nodes = []
    for node in nodes:
        hits = sum(1 for term in query_terms if term.lower() in _node_text(node))
        if hits:
            scored_nodes.append((hits, str(node.get("type") or ""), str(node.get("node_id") or ""), node["node_id"]))
    scored_nodes.sort(reverse=True)
    anchor_ids = {item[-1] for item in scored_nodes[:EGO_ANCHORS]}
    chain_candidates, chain_counts = reasoning._chain_edges(anchor_ids, edges)
    chain_candidates = _dedupe_edges(chain_candidates)
    query = _tokens(_query_text(diagnosis))
    vectors = [_tokens(_edge_text(edge, node_by_id)) for edge in chain_candidates]
    relevance = [_cosine(query, vector) for vector in vectors]
    ranked = sorted(range(len(chain_candidates)), key=lambda idx: relevance[idx], reverse=True)[:MAX_EDGES]
    selected_edges = [chain_candidates[idx] for idx in ranked]
    return _subgraph(selected_edges, node_by_id), {
        "algorithm": "C_egograph",
        "query_boundary": "diagnosis_anchors_only",
        "anchor_count": len(anchor_ids),
        "candidate_edges": len(chain_candidates),
        "chain_counts": chain_counts,
        "selection": "top80_local_token_cosine_within_1_2_hop_egograph",
    }


def _role_relevant_types(query_terms: list[str]) -> list[str]:
    return reasoning_retrieval.role_relevant_types(query_terms)


def _role_material_terms(query_terms: list[str]) -> tuple[set[str], set[str]]:
    return reasoning_retrieval.role_material_terms(query_terms)


def _score_nodes_by_type(nodes: list[dict], query_terms: list[str]) -> dict[str, list[tuple[int, int, str, str]]]:
    return reasoning_retrieval.score_nodes_by_type(nodes, query_terms)


def _type_balanced_anchor_ids(nodes: list[dict], query_terms: list[str], max_anchors: int = EGO_ANCHORS) -> tuple[set[str], dict]:
    return reasoning_retrieval.type_balanced_anchor_ids(nodes, query_terms, max_anchors=max_anchors)


def _algorithm_c2(nodes: list[dict], edges: list[dict], node_by_id: dict[str, dict], round_id: str, diagnosis: str) -> tuple[dict, dict]:
    query_terms = _anchor_query_terms(diagnosis)
    return reasoning_retrieval.ego_graph_subgraph(
        nodes,
        edges,
        node_by_id,
        diagnosis=diagnosis,
        query_terms=query_terms,
        transport_dimensions=reasoning.TRANSPORT_DIMENSIONS,
        max_edges=MAX_EDGES,
    )


def _edge_has_doc(edge: dict) -> bool:
    return bool(edge.get("source_doc_id"))


def _count_terms(subgraph: dict, node_by_id: dict[str, dict], terms: tuple[str, ...]) -> int:
    count = 0
    for edge in subgraph["edges"]:
        text = _edge_text(edge, node_by_id)
        if any(term in text for term in terms):
            count += 1
    return count


def _mainline_coverage(subgraph: dict, node_by_id: dict[str, dict], round_id: str) -> dict:
    keywords = EVAL_KEYWORDS[round_id]
    hits: dict[str, int] = {keyword: 0 for keyword in keywords}
    matching_edges = 0
    for edge in subgraph["edges"]:
        text = f" {_edge_text(edge, node_by_id)} "
        edge_hit = False
        for keyword in keywords:
            if keyword in text:
                hits[keyword] += 1
                edge_hit = True
        if edge_hit:
            matching_edges += 1
    return {"matching_edges": matching_edges, "keyword_hits": hits}


def _chain_integrity(subgraph: dict) -> int:
    out_rel: dict[str, set[str]] = defaultdict(set)
    in_rel: dict[str, set[str]] = defaultdict(set)
    for edge in subgraph["edges"]:
        out_rel[edge["src"]].add(str(edge.get("relation") or ""))
        in_rel[edge["dst"]].add(str(edge.get("relation") or ""))
    structure_relations = {"has_component", "replaces", "supports", "caused_by"}
    outcome_relations = {"improves", "causes_risk", "supports", "evidenced_by"}
    complete_nodes = {
        node_id
        for node_id in set(out_rel) | set(in_rel)
        if (out_rel[node_id] & outcome_relations and in_rel[node_id] & structure_relations)
        or (in_rel[node_id] & outcome_relations and out_rel[node_id] & structure_relations)
    }
    return len(complete_nodes)


def _metrics(subgraph: dict, node_by_id: dict[str, dict], round_id: str, algorithm_meta: dict) -> dict:
    edges = subgraph["edges"]
    doc_ids = {edge.get("source_doc_id") for edge in edges if edge.get("source_doc_id")}
    relations = {edge.get("relation") for edge in edges if edge.get("relation")}
    traceable = sum(1 for edge in edges if _edge_has_doc(edge))
    mainline = _mainline_coverage(subgraph, node_by_id, round_id)
    corr_edges = _count_terms(subgraph, node_by_id, CORR_TERMS)
    co2rr_edges = _count_terms(subgraph, node_by_id, CO2RR_TERMS)
    return {
        "round_id": round_id,
        "algorithm": algorithm_meta["algorithm"],
        "edge_count": len(edges),
        "mainline_edges": mainline["matching_edges"],
        "mainline_keyword_hits": mainline["keyword_hits"],
        "relation_types": len(relations),
        "doc_ids": len(doc_ids),
        "corr_edges": corr_edges,
        "co2rr_edges": co2rr_edges,
        "chain_integrity_paths": _chain_integrity(subgraph),
        "traceable_edges": traceable,
        "traceability": traceable / len(edges) if edges else 0.0,
        "metadata": algorithm_meta,
    }


def _render_comparison(rows: list[dict], out_dir: Path, kg_dir: Path) -> str:
    lines = [
        "# Step3 Retrieval Ablation Comparison",
        "",
        f"- KG input: `{kg_dir}`",
        f"- Output: `{out_dir}`",
        f"- Rounds: {len(reasoning.ROUND_ORDER)}",
        f"- Max edges per subgraph: {MAX_EDGES}",
        "- Retrieval input boundary: diagnosis text plus neutral lexical expansions only; taskbook target keywords are used only for evaluation metrics.",
        "- B embedding backend: local token cosine, not external embedding API.",
        "",
        "## Summary Table",
        "",
        "| algorithm | round | edges | mainline edges | chain paths | relation types | doc ids | CORR edges | CO2RR edges | traceability |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            "| {algorithm} | {round_id} | {edge_count} | {mainline_edges} | {chain_integrity_paths} | {relation_types} | {doc_ids} | {corr_edges} | {co2rr_edges} | {traceability:.2f} |".format(
                **row
            )
        )
    lines.extend(["", "## By-Round Best Scores", ""])
    for round_id in reasoning.ROUND_ORDER:
        subrows = [row for row in rows if row["round_id"] == round_id]
        best_mainline = max(subrows, key=lambda row: row["mainline_edges"])
        best_chain = max(subrows, key=lambda row: row["chain_integrity_paths"])
        lines.append(
            f"- {round_id}: mainline best = {best_mainline['algorithm']} ({best_mainline['mainline_edges']}), "
            f"chain best = {best_chain['algorithm']} ({best_chain['chain_integrity_paths']})"
        )
    lines.extend(["", "## Parameters", ""])
    for row in rows:
        lines.append(f"- {row['algorithm']} {row['round_id']}: `{json.dumps(row['metadata'], ensure_ascii=False)}`")
    return "\n".join(lines) + "\n"


ALGORITHMS = {
    "A_keyword_freq": _algorithm_a,
    "B_mmr": _algorithm_b,
    "C_egograph": _algorithm_c,
}

C_COMPARISON_ALGORITHMS = {
    "C_egograph": _algorithm_c,
    "C_egograph_v2": _algorithm_c2,
}


def run_ablation(
    kg_dir: str | Path = DEFAULT_KG_DIR,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    algorithms: dict[str, object] | None = None,
) -> list[dict]:
    kg_path = Path(kg_dir)
    output_path = Path(out_dir)
    nodes, edges, node_by_id = _load_kg(kg_path)
    rows: list[dict] = []
    selected_algorithms = algorithms or ALGORITHMS
    for algorithm_name, algorithm in selected_algorithms.items():
        for round_id in reasoning.ROUND_ORDER:
            diagnosis = reasoning.ROUND_DIAGNOSES[round_id]
            subgraph, meta = algorithm(nodes, edges, node_by_id, round_id, diagnosis)
            metrics = _metrics(subgraph, node_by_id, round_id, meta)
            round_dir = output_path / algorithm_name / round_id
            _write_json(round_dir / "subgraph.json", subgraph)
            _write_json(round_dir / "metrics.json", metrics)
            rows.append(metrics)
    _write_json(output_path / "metrics_all.json", rows)
    _write_text(output_path / "COMPARISON.md", _render_comparison(rows, output_path, kg_path))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Step3 retrieval ablation A/B/C without invoking the reasoning model.")
    parser.add_argument("--kg-dir", default=str(DEFAULT_KG_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--mode", choices=["abc", "c2"], default="abc")
    args = parser.parse_args()
    algorithms = C_COMPARISON_ALGORITHMS if args.mode == "c2" else ALGORITHMS
    rows = run_ablation(args.kg_dir, args.out_dir, algorithms=algorithms)
    if hasattr(__import__("sys").stdout, "reconfigure"):
        __import__("sys").stdout.reconfigure(encoding="utf-8")
    print(json.dumps({"rows": len(rows), "out_dir": str(args.out_dir)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
