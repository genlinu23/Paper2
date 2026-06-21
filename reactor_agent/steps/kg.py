from __future__ import annotations

import csv
import html
import json
import re
import time
import traceback
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .. import llm as llm_client
from ..contracts import ExtractedKGEdge, ExtractedKGNode, KGPaperEdges, KGPaperEntities, KGPaperExtraction
from .kg_visualize import build_visualizations


NODE_TYPES = [
    "Paper",
    "Claim",
    "Reactor",
    "Cathode",
    "Anode",
    "Separator",
    "Electrolyte",
    "Gas Feed",
    "Operating Condition",
    "Performance",
    "Failure Mode",
    "Diagnosis",
    "Next Hypothesis",
]
EDGE_TYPES = ["supports", "has_component", "improves", "causes_risk", "caused_by", "evidenced_by", "replaces"]
FACT_FIELDS = ("structure", "reaction", "membrane", "feed", "performance", "failure")
CLAIM_MAX_WORDS = 15

EDGE_SIGNATURE = {
    "has_component": ({"Reactor"}, {"Cathode", "Anode", "Separator", "Electrolyte", "Gas Feed"}),
    "improves": (
        {"Cathode", "Anode", "Separator", "Electrolyte", "Gas Feed", "Operating Condition", "Reactor"},
        {"Performance"},
    ),
    "causes_risk": (
        {"Cathode", "Anode", "Separator", "Electrolyte", "Gas Feed", "Operating Condition", "Reactor"},
        {"Failure Mode"},
    ),
    "caused_by": ({"Failure Mode"}, {"Operating Condition", "Separator", "Electrolyte", "Gas Feed", "Cathode", "Anode"}),
    "evidenced_by": ({"Diagnosis"}, {"Performance", "Operating Condition"}),
    "supports": ({"Paper"}, {"Claim"}),
    "replaces": (
        {"Cathode", "Anode", "Separator", "Electrolyte", "Gas Feed"},
        {"Cathode", "Anode", "Separator", "Electrolyte", "Gas Feed"},
    ),
}

CANONICAL_ENTITY_RULES = [
    (("flooding", "flooded", "water flooding", "electrode flooding"), "Failure Mode", "flooding"),
    (("high cell voltage", "high voltage", "cell voltage increase", "increased cell voltage", "overvoltage"), "Failure Mode", "high_cell_voltage"),
    (("low fe", "faradaic efficiency loss", "fe decline", "fe decrease", "decreased fe", "selectivity loss"), "Failure Mode", "low_FE"),
    (("dry-out", "dry out", "dryout", "membrane drying"), "Failure Mode", "dry_out"),
    (("cation depletion", "k+ depletion", "potassium depletion"), "Failure Mode", "cation_depletion"),
    (("spray blocked", "spray blockage", "spray nozzle blocked", "nozzle blockage"), "Failure Mode", "spray_blocked"),
    (("aem", "anion exchange membrane"), "Separator", "AEM"),
    (("ptfe porous diaphragm", "porous ptfe diaphragm", "ptfe diaphragm"), "Separator", "PTFE porous diaphragm"),
    (("koh electrolyte", "1 m koh", "1m koh", "potassium hydroxide electrolyte"), "Electrolyte", "KOH electrolyte"),
    (("gde", "gas diffusion electrode"), "Cathode", "GDE"),
    (("faradaic efficiency", "fe", "co faradaic efficiency"), "Performance", "FE"),
    (("cell voltage", "voltage"), "Performance", "cell voltage"),
    (("hfr", "high frequency resistance"), "Performance", "HFR"),
]

NEGATED_FAILURE_PATTERNS = (
    "no ",
    "without ",
    "absence of ",
    "suppressed ",
    "suppression of ",
    "prevented ",
    "prevention of ",
    "mitigated ",
    "mitigation of ",
    "avoided ",
    "avoidance of ",
    "stable ",
    "stability ",
)

EDGE_DEFINITIONS = [
    {
        "relation": "supports",
        "src_type": "Paper",
        "dst_type": "Claim",
        "definition": "A literature source supports a design-relevant causal or structural claim.",
    },
    {
        "relation": "has_component",
        "src_type": "Reactor",
        "dst_type": "Separator/Electrolyte/Gas Feed/Cathode/Anode",
        "definition": "A reactor architecture contains a named component.",
    },
    {
        "relation": "improves",
        "src_type": "Cathode/Anode/Separator/Electrolyte/Gas Feed/Operating Condition/Reactor",
        "dst_type": "Performance",
        "definition": "A component, feed, or operating condition improves a performance or transport function.",
    },
    {
        "relation": "causes_risk",
        "src_type": "Cathode/Anode/Separator/Electrolyte/Gas Feed/Operating Condition/Reactor",
        "dst_type": "Failure Mode",
        "definition": "A component, feed, or operating condition introduces or increases a failure risk.",
    },
    {
        "relation": "caused_by",
        "src_type": "Failure Mode",
        "dst_type": "Operating Condition/Separator/Electrolyte/Gas Feed/Cathode/Anode",
        "definition": "A failure mode is caused by a transport bottleneck, operating condition, or component limitation.",
    },
    {
        "relation": "evidenced_by",
        "src_type": "Diagnosis",
        "dst_type": "Performance/Operating Condition",
        "definition": "A diagnosis, failure mode, or claim is evidenced by measured voltage, EIS, FE, photo, or similar evidence.",
    },
    {
        "relation": "replaces",
        "src_type": "Cathode/Anode/Separator/Electrolyte/Gas Feed",
        "dst_type": "Cathode/Anode/Separator/Electrolyte/Gas Feed",
        "definition": "A next design or component replaces a previous bottleneck component.",
    },
]


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _props_to_dict(props: list[dict]) -> dict[str, str]:
    return {item["key"]: item["value"] for item in props if item.get("key")}


def _dict_to_props_json(props: dict | list | None) -> str:
    if isinstance(props, list):
        props = _props_to_dict(props)
    return json.dumps(props or {}, ensure_ascii=False, sort_keys=True)


def _normalize_node_id(node_id: str) -> str:
    return node_id.strip().replace(" ", "_")


def _slug(text: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", text.strip())
    value = re.sub(r"_+", "_", value).strip("_")
    return value or "unnamed"


def _node_type_slug(node_type: str) -> str:
    return _slug(node_type)


def _canonical_entity_from_text(text: str) -> tuple[str, str] | None:
    lowered = f" {text.lower()} "
    for aliases, node_type, label in CANONICAL_ENTITY_RULES:
        for alias in aliases:
            pattern = r"(?<![A-Za-z0-9])" + re.escape(alias.lower()) + r"(?![A-Za-z0-9])"
            if re.search(pattern, lowered):
                return node_type, label
    return None


def _canonical_domain_node(node: dict) -> dict | None:
    node = dict(node)
    if node["type"] not in NODE_TYPES:
        return None
    label = str(node.get("label") or "").strip()
    if not label:
        return None
    canonical = _canonical_entity_from_text(f"{label} {node.get('node_id', '')}")
    if canonical:
        node["type"], node["label"] = canonical
    if node["type"] == "Failure Mode" and _is_negated_failure_label(node["label"]):
        node["type"] = "Performance"
    if node["type"] == "Claim" and _claim_too_long(node["label"]):
        return None
    node["node_id"] = _canonical_node_id(node)
    return node


def _claim_too_long(label: str) -> bool:
    words = re.findall(r"[A-Za-z0-9_+-]+|[\u4e00-\u9fff]", label)
    return len(words) > CLAIM_MAX_WORDS


def _is_negated_failure_label(label: str) -> bool:
    lowered = label.strip().lower()
    return any(lowered.startswith(pattern) or f" {pattern}" in lowered for pattern in NEGATED_FAILURE_PATTERNS)


def _canonical_node_id(node: dict) -> str:
    if node["type"] == "Paper":
        raw_node_id = str(node.get("node_id") or "").strip()
        if raw_node_id.startswith("paper:"):
            return raw_node_id
        doc_id = _props_to_dict(node.get("props", [])).get("doc_id")
        if doc_id:
            return f"paper:{doc_id}"
    canonical = _canonical_entity_from_text(f"{node.get('label', '')} {node.get('node_id', '')}")
    if canonical:
        node_type, label = canonical
        return f"{_node_type_slug(node_type)}:{_slug(label)}"
    label = str(node.get("label") or node["node_id"]).strip()
    return f"{_node_type_slug(node['type'])}:{_slug(label)}"


def _edge_traceable(edge: dict) -> bool:
    return bool(edge.get("source_doc_id") or edge.get("experiment_ref"))


def check_edge_signature(edge: dict, nodes: dict[str, dict]) -> bool:
    relation = edge.get("relation")
    if relation not in EDGE_SIGNATURE:
        return False
    src = nodes.get(edge.get("src"))
    dst = nodes.get(edge.get("dst"))
    if not src or not dst:
        return False
    ok_src, ok_dst = EDGE_SIGNATURE[relation]
    return src.get("type") in ok_src and dst.get("type") in ok_dst


def _edge_semantically_allowed(edge: dict, nodes: dict[str, dict]) -> bool:
    src = nodes.get(edge.get("src"))
    dst = nodes.get(edge.get("dst"))
    if not src or not dst:
        return False
    if edge.get("relation") == "causes_risk" and _is_negated_failure_label(dst.get("label", "")):
        return False
    if edge.get("relation") == "caused_by" and _is_negated_failure_label(src.get("label", "")):
        return False
    return True


def _load_filtered_doc_ids(filtered_core: Path) -> set[str]:
    rows = _read_json(filtered_core)
    if not isinstance(rows, list):
        raise ValueError(f"filtered core must be a JSON list: {filtered_core}")
    return {row["doc_id"] for row in rows}


def _paper_facts_payload(paper: dict) -> dict:
    payload = {"doc_id": paper["doc_id"], "doi": paper["doi"], "facts": {}}
    for field in FACT_FIELDS:
        payload["facts"][field] = [
            {
                "value": fact.get("value"),
                "chunk_id": fact.get("chunk_id"),
                "section_title": fact.get("section_title"),
            }
            for fact in paper.get(field, [])
            if fact.get("value") != "not_mentioned"
        ]
    return payload


def _extract_paper_entities(paper: dict) -> KGPaperEntities:
    system = (
        "You are Step A of a reactor knowledge graph extractor. Input is one literature paper's extracted facts "
        "(structure/reaction/membrane/feed/performance/failure, each with chunk_id). Extract normalized entity nodes only. "
        "Use only these node types: Paper, Claim, Reactor, Cathode, Anode, Separator, Electrolyte, Gas Feed, "
        "Operating Condition, Performance, Failure Mode, Diagnosis, Next Hypothesis. "
        "Do not output edges in this step. Use stable node_id values that can be reused by Step B. "
        "Always create one Paper node with node_id paper:<doc_id>. Prefer domain entities over Claim nodes. "
        "Only use Claim when a short statement cannot be normalized into the domain types, and keep each Claim label <=15 words. "
        "Normalize common entities exactly: flooding, high_cell_voltage, low_FE, dry_out, cation_depletion, spray_blocked, "
        "AEM, PTFE porous diaphragm, KOH electrolyte, GDE, FE, cell voltage, HFR. "
        "Failure Mode labels must be adverse phenomena. Do not create Failure Mode nodes for absence, prevention, suppression, "
        "mitigation, or stability statements; those are Performance or Diagnosis if needed. "
        "Do not say AEM provides K+. Do not classify PTFE porous diaphragm as an ion exchange membrane."
    )
    user = json.dumps(_paper_facts_payload(paper), ensure_ascii=False)
    result = llm_client.call(role="kg", system=system, user=user, schema=KGPaperEntities)
    if result.doc_id != paper["doc_id"]:
        raise ValueError(f"KG entity extraction returned mismatched doc_id: {result.doc_id} != {paper['doc_id']}")
    return result


def _extract_paper_edges(paper: dict, entities: KGPaperEntities) -> KGPaperEdges:
    allowed_nodes = []
    for node in entities.nodes:
        node_payload = node.model_dump(mode="json")
        canonical = _canonical_domain_node(node_payload)
        if canonical is not None:
            allowed_nodes.append(
                {
                    "node_id": canonical["node_id"],
                    "type": canonical["type"],
                    "label": canonical["label"],
                }
            )
    system = (
        "You are Step B of a reactor knowledge graph extractor. Create edges only between the supplied Step A nodes. "
        "Use only these relations: supports, has_component, improves, causes_risk, caused_by, evidenced_by, replaces. "
        "Every edge must use exact src/dst node_id values from allowed_nodes. Do not create new nodes. "
        "Every edge must include source_doc_id and source_chunk_id from the fact that explicitly supports the relationship. "
        "Only create an edge when the source text explicitly states causation, improvement, risk, evidence, support, replacement, or component membership. "
        "Correlation, co-occurrence, and adjacent facts are not causal edges. "
        "Before outputting an edge, enforce the endpoint signature table: "
        "has_component Reactor->Cathode/Anode/Separator/Electrolyte/Gas Feed; "
        "improves Cathode/Anode/Separator/Electrolyte/Gas Feed/Operating Condition/Reactor->Performance; "
        "causes_risk Cathode/Anode/Separator/Electrolyte/Gas Feed/Operating Condition/Reactor->Failure Mode; "
        "caused_by Failure Mode->Operating Condition/Separator/Electrolyte/Gas Feed/Cathode/Anode; "
        "evidenced_by Diagnosis->Performance/Operating Condition; supports Paper->Claim; "
        "replaces Cathode/Anode/Separator/Electrolyte/Gas Feed->Cathode/Anode/Separator/Electrolyte/Gas Feed. "
        "Do not output an edge if its endpoint types do not match this table. "
        "causes_risk must point to a Failure Mode and cannot point to a benefit, material, stability statement, absence of failure, "
        "or Performance node."
    )
    user = json.dumps({"paper": _paper_facts_payload(paper), "allowed_nodes": allowed_nodes}, ensure_ascii=False)
    result = llm_client.call(role="kg", system=system, user=user, schema=KGPaperEdges)
    if result.doc_id != paper["doc_id"]:
        raise ValueError(f"KG edge extraction returned mismatched doc_id: {result.doc_id} != {paper['doc_id']}")
    return result


def _extract_paper_kg(paper: dict) -> KGPaperExtraction:
    entities = _extract_paper_entities(paper)
    edges = _extract_paper_edges(paper, entities)
    return KGPaperExtraction(doc_id=paper["doc_id"], nodes=entities.nodes, edges=edges.edges)


def _extract_with_retry(
    paper: dict,
    out_file: Path,
    max_retries: int,
    retry_sleep_s: float,
    overwrite: bool,
) -> dict:
    if out_file.exists() and not overwrite:
        result = KGPaperExtraction.model_validate(_read_json(out_file))
        return {"doc_id": paper["doc_id"], "status": "skipped", "result": result}

    for attempt in range(1, max_retries + 2):
        try:
            result = _extract_paper_kg(paper)
            _write_json(out_file, result.model_dump(mode="json"))
            return {"doc_id": paper["doc_id"], "status": "ok", "result": result, "attempt": attempt}
        except Exception as exc:  # noqa: BLE001
            if attempt > max_retries:
                return {
                    "doc_id": paper["doc_id"],
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc(),
                    "attempt": attempt,
                }
            time.sleep(retry_sleep_s * attempt)
    raise RuntimeError("unreachable retry state")


def _merge_extractions(extractions: list[KGPaperExtraction], core_by_doc: dict[str, dict]) -> tuple[list[dict], list[dict], list[dict]]:
    nodes: dict[str, dict] = {}
    edges: dict[tuple[str, str, str, str | None, str | None], dict] = {}
    discarded_edges: list[dict] = []

    for extraction in extractions:
        doc_id = extraction.doc_id
        core = core_by_doc.get(doc_id, {})
        paper_id = f"paper:{doc_id}"
        nodes.setdefault(
            paper_id,
            {
                "node_id": paper_id,
                "type": "Paper",
                "label": core.get("title") or core.get("doi") or doc_id,
                "props": {"doc_id": doc_id, "doi": core.get("doi", ""), "lib": core.get("lib", ""), "class_name": core.get("class_name", "")},
            },
        )
        for node_model in extraction.nodes:
            raw_node = node_model.model_dump(mode="json")
            node = _canonical_domain_node(raw_node)
            if node is None:
                continue
            node_id = node["node_id"]
            props = _props_to_dict(node.get("props", []))
            if node["type"] == "Paper":
                node_id = paper_id
                props.update({"doc_id": doc_id, "doi": core.get("doi", "")})
            nodes.setdefault(
                node_id,
                {
                    "node_id": node_id,
                    "type": node["type"],
                    "label": node["label"],
                    "props": props,
                },
            )

        for edge_model in extraction.edges:
            raw_edge = edge_model.model_dump(mode="json")
            edge = dict(raw_edge)
            edge["src"] = _normalize_node_id(edge["src"])
            edge["dst"] = _normalize_node_id(edge["dst"])
            if edge["src"] not in nodes:
                src_alias = _canonical_entity_from_text(edge["src"])
                if src_alias:
                    edge["src"] = f"{_node_type_slug(src_alias[0])}:{_slug(src_alias[1])}"
            if edge["dst"] not in nodes:
                dst_alias = _canonical_entity_from_text(edge["dst"])
                if dst_alias:
                    edge["dst"] = f"{_node_type_slug(dst_alias[0])}:{_slug(dst_alias[1])}"
            if not _edge_traceable(edge):
                discarded_edges.append({"reason": "not_traceable", "doc_id": doc_id, "edge": raw_edge})
                continue
            src = edge["src"]
            dst = edge["dst"]
            if src not in nodes and src.startswith("paper:"):
                nodes[src] = nodes[paper_id]
            if src not in nodes or dst not in nodes:
                # Keep only edges whose endpoints are part of the ontology node table.
                discarded_edges.append({"reason": "missing_endpoint", "doc_id": doc_id, "edge": raw_edge})
                continue
            if not check_edge_signature(edge, nodes):
                discarded_edges.append(
                    {
                        "reason": "edge_signature_violation",
                        "doc_id": doc_id,
                        "src_type": nodes[src]["type"],
                        "dst_type": nodes[dst]["type"],
                        "edge": edge,
                    }
                )
                continue
            if not _edge_semantically_allowed(edge, nodes):
                discarded_edges.append({"reason": "negated_failure_statement", "doc_id": doc_id, "edge": edge})
                continue
            key = (src, dst, edge["relation"], edge.get("source_doc_id"), edge.get("source_chunk_id"))
            edges.setdefault(
                key,
                {
                    "src": src,
                    "dst": dst,
                    "relation": edge["relation"],
                    "source_doc_id": edge.get("source_doc_id"),
                    "source_chunk_id": edge.get("source_chunk_id"),
                    "experiment_ref": edge.get("experiment_ref"),
                },
            )

    return list(nodes.values()), list(edges.values()), discarded_edges


def validate_kg(nodes: list[dict], edges: list[dict]) -> list[str]:
    problems: list[str] = []
    node_ids = {node["node_id"] for node in nodes}
    nodes_by_id = {node["node_id"]: node for node in nodes}
    for node in nodes:
        if node["type"] not in NODE_TYPES:
            problems.append(f"invalid node type: {node['node_id']} {node['type']}")
    for edge in edges:
        if edge["relation"] not in EDGE_TYPES:
            problems.append(f"invalid edge relation: {edge}")
        if edge["src"] not in node_ids or edge["dst"] not in node_ids:
            problems.append(f"edge endpoint missing: {edge}")
        if not _edge_traceable(edge):
            problems.append(f"edge not traceable: {edge}")
        if not check_edge_signature(edge, nodes_by_id):
            problems.append(f"edge signature violation: {edge}")
        if not _edge_semantically_allowed(edge, nodes_by_id):
            problems.append(f"edge semantic violation: {edge}")
    return problems


def _write_relation_definitions(out_path: Path) -> None:
    _write_json(out_path / "kg_relation_definitions.json", EDGE_DEFINITIONS)
    _write_csv(out_path / "kg_relation_definitions.csv", EDGE_DEFINITIONS, ["relation", "src_type", "dst_type", "definition"])


def _drop_orphan_claim_nodes(nodes: list[dict], edges: list[dict]) -> list[dict]:
    connected = {edge["src"] for edge in edges} | {edge["dst"] for edge in edges}
    return [node for node in nodes if node["type"] != "Claim" or node["node_id"] in connected]


def _write_outputs(out_path: Path, nodes: list[dict], edges: list[dict], failures: list[dict], discarded_edges: list[dict] | None = None) -> dict:
    nodes = _drop_orphan_claim_nodes(nodes, edges)
    node_rows = [
        {
            "node_id": node["node_id"],
            "type": node["type"],
            "label": node["label"],
            "props": node.get("props", {}),
        }
        for node in sorted(nodes, key=lambda row: (row["type"], row["node_id"]))
    ]
    edge_rows = sorted(edges, key=lambda row: (row["relation"], row["src"], row["dst"], row.get("source_chunk_id") or ""))
    problems = validate_kg(node_rows, edge_rows)
    if problems:
        raise ValueError("KG validation failed:\n" + "\n".join(problems[:20]))

    _write_json(out_path / "kg_nodes.json", node_rows)
    _write_json(out_path / "kg_edges.json", edge_rows)
    _write_csv(
        out_path / "kg_nodes.csv",
        [
            {
                "node_id": row["node_id"],
                "type": row["type"],
                "label": row["label"],
                "props": _dict_to_props_json(row.get("props")),
            }
            for row in node_rows
        ],
        ["node_id", "type", "label", "props"],
    )
    _write_csv(
        out_path / "kg_edges.csv",
        edge_rows,
        ["src", "dst", "relation", "source_doc_id", "source_chunk_id", "experiment_ref"],
    )
    _write_relation_definitions(out_path)
    nodes_by_id = {node["node_id"]: node for node in node_rows}
    claim_nodes = sum(1 for node in node_rows if node["type"] == "Claim")
    claim_edges = sum(1 for edge in edge_rows if nodes_by_id[edge["src"]]["type"] == "Claim" or nodes_by_id[edge["dst"]]["type"] == "Claim")
    causes_risk = [edge for edge in edge_rows if edge["relation"] == "causes_risk"]
    causes_risk_to_failure_mode = sum(1 for edge in causes_risk if nodes_by_id[edge["dst"]]["type"] == "Failure Mode")
    summary = {
        "nodes": len(node_rows),
        "edges": len(edge_rows),
        "failures": len(failures),
        "discarded_edges": len(discarded_edges or []),
        "node_types": dict(Counter(node["type"] for node in node_rows)),
        "relations": dict(Counter(edge["relation"] for edge in edge_rows)),
        "traceable_edges": sum(1 for edge in edge_rows if _edge_traceable(edge)),
        "claim_node_ratio": claim_nodes / max(len(node_rows), 1),
        "claim_edge_ratio": claim_edges / max(len(edge_rows), 1),
        "causes_risk_to_failure_mode_ratio": causes_risk_to_failure_mode / max(len(causes_risk), 1),
    }
    _write_json(out_path / "kg_summary.json", summary)
    _write_json(out_path / "failures.json", failures)
    _write_json(out_path / "discarded_edges.json", discarded_edges or [])
    export_kg_view(out_path, out_path)
    return summary


def build_kg(
    step1_dir: str | Path,
    filtered_core: str | Path,
    kg_dir: str | Path,
    concurrency: int = 32,
    max_retries: int = 3,
    retry_sleep_s: float = 5.0,
    overwrite: bool = False,
    limit: int | None = None,
    visualize: bool = True,
    viz_max_full: int = 400,
    viz_cache_lib: bool = True,
) -> dict:
    step1_path = Path(step1_dir)
    out_path = Path(kg_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    filtered_ids = _load_filtered_doc_ids(Path(filtered_core))
    facts_rows = _read_json(step1_path / "paper_facts.json")
    core_rows = _read_json(step1_path / "core_papers.json")
    if not isinstance(facts_rows, list) or not isinstance(core_rows, list):
        raise ValueError("paper_facts.json and core_papers.json must be JSON lists")
    core_by_doc = {row["doc_id"]: row for row in core_rows}
    selected = [row for row in facts_rows if row["doc_id"] in filtered_ids]
    if limit is not None:
        selected = selected[:limit]
    if not selected:
        raise ValueError("no Step1 facts matched filtered core doc_ids")

    per_doc_dir = out_path / "kg_by_doc"
    per_doc_dir.mkdir(parents=True, exist_ok=True)
    failures: list[dict] = []
    results: list[KGPaperExtraction] = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(
                _extract_with_retry,
                paper,
                per_doc_dir / f"{paper['doc_id']}.json",
                max_retries,
                retry_sleep_s,
                overwrite,
            ): paper["doc_id"]
            for paper in selected
        }
        completed = 0
        for future in as_completed(futures):
            completed += 1
            item = future.result()
            if item["status"] in {"ok", "skipped"}:
                results.append(item["result"])
            else:
                failures.append({k: v for k, v in item.items() if k != "result"})
            if completed == len(selected) or completed % 10 == 0:
                nodes, edges, discarded_edges = _merge_extractions(results, core_by_doc)
                _write_json(
                    out_path / "progress.json",
                    {"completed": completed, "total": len(selected), "success": len(results), "failed": len(failures)},
                )
                _write_outputs(out_path, nodes, edges, failures, discarded_edges)

    nodes, edges, discarded_edges = _merge_extractions(results, core_by_doc)
    summary = _write_outputs(out_path, nodes, edges, failures, discarded_edges)
    if visualize:
        summary["visualization"] = build_visualizations(out_path, out_path / "viz", max_full=viz_max_full, cache_lib=viz_cache_lib)
    return summary


def query_subgraph(kg_dir: str | Path, failure_modes: list[str]) -> dict:
    kg_path = Path(kg_dir)
    nodes = _read_json(kg_path / "kg_nodes.json")
    edges = _read_json(kg_path / "kg_edges.json")
    wanted = {item.lower() for item in failure_modes}
    node_by_id = {node["node_id"]: node for node in nodes}
    seed_ids = {node["node_id"] for node in nodes if node["type"] == "Failure Mode" and node["label"].lower() in wanted}
    edge_subset = [edge for edge in edges if edge["src"] in seed_ids or edge["dst"] in seed_ids]
    node_ids = seed_ids | {edge["src"] for edge in edge_subset} | {edge["dst"] for edge in edge_subset}
    return {"nodes": [node_by_id[node_id] for node_id in sorted(node_ids) if node_id in node_by_id], "edges": edge_subset}


def export_kg_view(kg_dir: str | Path, out_dir: str | Path) -> dict:
    kg_path = Path(kg_dir)
    out_path = Path(out_dir)
    nodes = _read_json(kg_path / "kg_nodes.json")
    edges = _read_json(kg_path / "kg_edges.json")
    html_path = out_path / "kg_causal_view.html"
    svg_path = out_path / "kg_causal_snapshot.svg"
    _write_causal_html(html_path, nodes, edges)
    _write_causal_svg(svg_path, nodes, edges)
    return {"html": str(html_path), "svg": str(svg_path)}


def _write_causal_html(path: Path, nodes: list[dict], edges: list[dict]) -> None:
    node_by_id = {node["node_id"]: node for node in nodes}
    rows = []
    for edge in edges[:1500]:
        src = node_by_id.get(edge["src"], {})
        dst = node_by_id.get(edge["dst"], {})
        rows.append(
            "<tr>"
            f"<td>{html.escape(edge['relation'])}</td>"
            f"<td>{html.escape(src.get('type', ''))}</td>"
            f"<td>{html.escape(src.get('label', edge['src']))}</td>"
            f"<td>{html.escape(dst.get('type', ''))}</td>"
            f"<td>{html.escape(dst.get('label', edge['dst']))}</td>"
            f"<td>{html.escape(edge.get('source_doc_id') or '')}</td>"
            f"<td>{html.escape(edge.get('source_chunk_id') or '')}</td>"
            "</tr>"
        )
    metrics = dict(Counter(edge["relation"] for edge in edges))
    metric_html = " ".join(f"<span>{html.escape(k)}: {v}</span>" for k, v in metrics.items())
    path.write_text(
        f"""<!doctype html>
<html><head><meta charset="utf-8"><title>D2 Causal KG</title>
<style>
body{{font-family:Arial,sans-serif;margin:24px;color:#17202a}}
span{{display:inline-block;border:1px solid #ccd2da;border-radius:6px;padding:4px 7px;margin:0 6px 8px 0}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border:1px solid #d6d9de;padding:6px 8px;vertical-align:top}}
th{{background:#f2f4f7;position:sticky;top:0}}
</style></head><body>
<h1>D2 Causal KG</h1>
<p>Nodes: {len(nodes)} Edges: {len(edges)}</p>
<div>{metric_html}</div>
<table><thead><tr><th>Relation</th><th>Src type</th><th>Src</th><th>Dst type</th><th>Dst</th><th>Doc</th><th>Chunk</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
</body></html>""",
        encoding="utf-8",
    )


def _write_causal_svg(path: Path, nodes: list[dict], edges: list[dict]) -> None:
    relation_counts = Counter(edge["relation"] for edge in edges)
    node_type_counts = Counter(node["type"] for node in nodes)
    width, height = 1000, 650
    bars = []
    max_count = max(relation_counts.values() or [1])
    y = 70
    for relation, count in relation_counts.most_common():
        bar_w = int(520 * count / max_count)
        bars.append(f'<text x="30" y="{y+14}" font-size="14">{html.escape(relation)} {count}</text>')
        bars.append(f'<rect x="180" y="{y}" width="{bar_w}" height="20" fill="#4f83cc"/>')
        y += 34
    node_text = []
    y2 = 70
    for node_type, count in node_type_counts.most_common():
        node_text.append(f'<text x="760" y="{y2}" font-size="14">{html.escape(node_type)}: {count}</text>')
        y2 += 24
    path.write_text(
        f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
<rect width="100%" height="100%" fill="white"/>
<text x="30" y="35" font-size="22" font-family="Arial">D2 Causal KG Snapshot</text>
<text x="760" y="35" font-size="16" font-family="Arial">Node types</text>
<g font-family="Arial">{''.join(bars)}{''.join(node_text)}</g>
</svg>""",
        encoding="utf-8",
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Build Reactor Step 2 causal KG from Step 1 facts.")
    parser.add_argument("--step1-dir", required=True)
    parser.add_argument("--filtered-core", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--concurrency", type=int, default=32)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--retry-sleep-s", type=float, default=5.0)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--skip-viz", action="store_true", help="Do not generate the Step2 KG HTML visualization bundle.")
    parser.add_argument("--viz-max-full", type=int, default=400, help="Maximum nodes shown in viz/overview.html.")
    parser.add_argument("--no-viz-cache-lib", action="store_true", help="Use CDN instead of downloading vis-network into viz/.")
    args = parser.parse_args()
    summary = build_kg(
        args.step1_dir,
        args.filtered_core,
        args.out_dir,
        concurrency=args.concurrency,
        max_retries=args.max_retries,
        retry_sleep_s=args.retry_sleep_s,
        overwrite=args.overwrite,
        limit=args.limit,
        visualize=not args.skip_viz,
        viz_max_full=args.viz_max_full,
        viz_cache_lib=not args.no_viz_cache_lib,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
