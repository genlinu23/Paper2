from __future__ import annotations

import json
import re
import csv
import sys
from pathlib import Path

from .. import llm as llm_client
from ..contracts import BuildLayer, BuildSheet, LiteratureRef, ReactorRecommendation, Step3RunConfig
from . import reasoning_retrieval


DEFAULT_REASONING_MODEL = "gpt-5.4"
DEFAULT_REASONING_ROLE = "reasoning"
ROUND_ORDER = ["R1", "R2", "R3", "R4", "R5", "R6", "R7"]
ROUND_DIAGNOSES = {
    "R1": "固态电解质层带来过高欧姆阻抗",
    "R2": "连续液层造成压力不平衡、传质不稳和额外电阻",
    "R3": "缺水导致干涸，且局部缺少 K+ 环境",
    "R4": "静态储水/储 K+ 会逐渐耗尽",
    "R5": "碳纸孔结构不适合雾滴输运",
    "R6": "PTL 支持气体、雾滴和固体催化位点接触",
    "R7": "喷雾提供 H2O 和 K+，PTFE 提供物理隔离并降低膜成本",
}

FULL_ROUND_DIAGNOSES = {
    "R1": (
        "The current baseline has a thick solid-electrolyte transport path and the dominant diagnosis is excessive "
        "ohmic impedance. The next reasoning step should focus on shortening ion-transport distance, lowering "
        "membrane/electrolyte resistance, and preserving traceable gas access and mechanical stability."
    ),
    "R2": (
        "The prior attempt reduced the solid-electrolyte resistance directionally, but the remaining diagnosis is that "
        "a continuous liquid layer creates pressure imbalance, unstable mass transport, and extra resistance. The next "
        "reasoning step should avoid a persistent flooding-prone liquid film while keeping ion transport and gas access "
        "controlled."
    ),
    "R3": (
        "After reducing continuous-liquid-layer problems, the remaining diagnosis is cathode-side dry-out and a local "
        "lack of K+ / cation environment. The next reasoning step should maintain water supply and cation availability "
        "near the reaction interface without reintroducing unstable flooding or large ohmic loss."
    ),
    "R4": (
        "The prior direction introduced local water and K+ availability, but a static reservoir of water or K+ will be "
        "depleted during operation. The next reasoning step should replace static storage with a replenishable transport "
        "path that maintains water management and cation availability over time."
    ),
    "R5": (
        "The system has moved toward gas-aerosol-solid contacting, but the diagnosis is that the carbon-paper pore "
        "structure is not well matched to aerosol or droplet transport. In the CORR / CO-reduction operating direction, "
        "the next reasoning step should seek a more open and stable porous transport path for gas, aerosol, and catalyst "
        "contact without specifying the next material stack."
    ),
    "R6": (
        "The prior cathode transport problem points to the need for a porous transport layer that can support gas, "
        "aerosol droplets, and solid catalytic sites in contact. In the CORR / CO-reduction direction, the next reasoning "
        "step should focus on stabilizing gas-aerosol-solid contact, reducing local transport loss, and avoiding flooding "
        "or dry-out."
    ),
    "R7": (
        "The remaining diagnosis is in a CORR / CO-reduction reactor direction: spray or aerosol delivery must provide "
        "H2O and K+ / cation availability, while PTFE is only a physical isolation and cost-reduction element rather than "
        "an ion-conducting membrane. The next reasoning step should optimize transport-function allocation, membrane cost, "
        "gas access, cation supply, and stability without prescribing the final component stack."
    ),
}

DIAGNOSIS_MODES = {
    "brief": ROUND_DIAGNOSES,
    "full": FULL_ROUND_DIAGNOSES,
}

DIAGNOSIS_ANSWER_PATTERNS = (
    r"\bpt@ptl\b.{0,80}\bptfe\b.{0,80}\bcu\b.{0,80}\bcarbon[- ]paper\b",
    r"\bcu\b.{0,40}\bcarbon[- ]paper\b.{0,80}\bpt@ptl\b",
    r"\bnext\b.{0,60}\b(pt@ptl|pt-loaded ptl)\b.{0,120}\b(cu|copper)\b.{0,40}\bcarbon[- ]paper\b",
    r"\bshould\b.{0,60}\b(use|adopt|select)\b.{0,120}\b(pt@ptl|pt-loaded ptl)\b",
    r"\bshould\b.{0,60}\b(use|adopt|select)\b.{0,120}\bcu\b.{0,40}\bcarbon[- ]paper\b",
)

TASKBOOK_RECOMMENDED_STRUCTURES = {
    "R1": "CORR / solid-electrolyte-layer / HOR solid MEA",
    "R2": "Replace the middle layer with 1 M KOH liquid electrolyte",
    "R3": "Double-sided gas: CORR / AEM / HOR",
    "R4": "Water-retention layer plus pre-cation layer",
    "R5": "Anode H2 + 1 M KOH spray, carbon-paper electrode, cathode CO",
    "R6": "Pt@porous-PTL anode, H2 + KOH aerosol",
    "R7": "Pt@PTL anode / porous PTFE diaphragm / Cu@carbon-paper cathode",
}

TASKBOOK_STRUCTURE_TERMS = {
    "R1": ("solid electrolyte", "solid-electrolyte", "solid mea"),
    "R2": ("1 m koh", "liquid electrolyte"),
    "R3": ("double-sided gas", "aem", "hor"),
    "R4": ("water-retention", "water retention", "pre-cation", "cation"),
    "R5": ("spray", "aerosol", "carbon paper"),
    "R6": ("ptl", "pt@ptl", "aerosol"),
    "R7": ("ptfe", "porous diaphragm", "cu", "carbon"),
}

TASKBOOK_STRUCTURE_REQUIREMENTS = {
    "R1": (("corr", "co reduction", "co electroreduction"), ("solid electrolyte", "solid-electrolyte", "solid mea"), ("hor",)),
    "R2": (("1 m koh", "koh"), ("liquid electrolyte", "liquid layer"),),
    "R3": (("double-sided gas", "double sided gas"), ("aem",), ("hor",)),
    "R4": (("water-retention", "water retention", "water retaining"), ("pre-cation", "pre cation", "cation layer"),),
    "R5": (("h2",), ("spray", "aerosol"), ("carbon paper", "carbon-paper"), (" co ", "corr", "co reduction")),
    "R6": (("pt@ptl", "ptl"), ("h2",), ("koh aerosol", "aerosol")),
    "R7": (("pt@ptl", "ptl"), ("ptfe", "porous diaphragm"), ("cu", "copper"), ("carbon paper", "carbon-paper", "carbon-paper cathode")),
}

ROUND_REASONING_TARGETS = {
    "R1": (
        ("ohmic", "resistance", "impedance", "ion transport", "ionic", "conductivity", "solid electrolyte", "solid-electrolyte"),
    ),
    "R2": (
        ("liquid", "liquid layer", "pressure", "pressure imbalance", "mass transport", "transport", "resistance"),
    ),
    "R3": (
        ("water", "h2o", "dry", "dry-out", "dryout", "dehydration"),
        ("k+", "cation", "potassium", "alkali"),
    ),
    "R4": (
        ("storage", "reservoir", "retention", "water-retention", "water retention"),
        ("depletion", "deplete", "exhaust", "consum", "drift"),
    ),
    "R5": (
        ("carbon paper", "carbon-paper", "pore", "porous", "孔"),
        ("droplet", "aerosol", "spray", "雾滴", "transport"),
    ),
    "R6": (
        ("ptl", "porous transport layer"),
        ("gas-liquid-solid", "gas-aerosol-solid", "three-phase", "triple-phase", "gas", "aerosol", "solid", "contact"),
    ),
    "R7": (
        ("spray", "aerosol", "喷雾"),
        ("h2o", "water", "k+", "cation", "potassium", "钾"),
        ("ptfe", "porous diaphragm", "diaphragm", "separator", "隔膜"),
        ("cost", "成本", "isolation", "isolate", "separation", "physical isolation", "隔离"),
    ),
}

RETRIEVAL_COMPONENT_ANCHOR_TERMS = {
    "R7": (
        "CORR performance",
        "electrochemical CO reduction reaction",
        "CO reduction",
        "CO electroreduction",
        "CO feed",
        "CO gas feed",
        "carbon monoxide",
        "Cu cathode",
        "Cu carbon paper",
        "carbon paper cathode",
        "Pt@PTL",
        "PTL anode",
        "Pt-RuO2",
        "titanium felt PTL",
        "Pt catalyst",
        "porous transport layer",
        "H2 feed",
        "HOR",
        "hydrogen oxidation",
        "KOH aerosol",
    ),
}

TRANSPORT_DIMENSIONS = {
    "ion_transport": ("ion transport", "ionic conductivity", "ion conduction", "membrane resistance", "anion transport", "cation transport"),
    "water_management": ("water management", "flooding", "dry-out", "dry out", "water retention", "humidification", "wettability", "water transport"),
    "gas_access": ("gas diffusion", "gas access", "triple-phase", "three-phase", "gde", "porous transport", "mass transport", "gas transport"),
    "cation_availability": ("cation", "k+", "potassium", "alkali metal cation", "carbonate"),
    "ohmic_loss": ("ohmic", "cell voltage", "hfr", "resistance", "overpotential", "impedance"),
    "mechanical_stability": ("mechanical", "stability", "degradation", "crack", "delamination", "sealing", "durability"),
}

DIAGNOSIS_TERM_LEXICON = {
    "固态": ["solid"],
    "电解质": ["electrolyte"],
    "欧姆": ["ohmic", "resistance"],
    "阻抗": ["resistance", "impedance"],
    "连续": ["continuous"],
    "液层": ["liquid layer", "liquid"],
    "压力": ["pressure"],
    "传质": ["mass transport", "transport"],
    "电阻": ["resistance"],
    "缺水": ["water", "dry"],
    "干涸": ["dry", "dry-out"],
    "局部": ["local"],
    "K+": ["K+"],
    "储水": ["water storage", "water"],
    "储 K+": ["K+", "storage"],
    "耗尽": ["depletion", "depleted"],
    "碳纸": ["carbon paper"],
    "孔": ["pore", "porous"],
    "雾滴": ["droplet", "aerosol"],
    "输运": ["transport"],
    "PTL": ["PTL", "porous transport layer"],
    "气体": ["gas"],
    "固体": ["solid"],
    "催化": ["catalytic", "catalyst"],
    "接触": ["contact", "contacting"],
    "喷雾": ["spray", "aerosol"],
    "H2O": ["H2O", "water"],
    "PTFE": ["PTFE"],
    "物理隔离": ["physical separation", "separator"],
    "隔离": ["separation", "separator"],
    "膜": ["membrane"],
    "成本": ["cost"],
}

DOI_METADATA_PATH = Path(r"C:\Users\logan\Desktop\project2_strict\doi_pdf_filter_audit_v1\unique_doi_metadata.csv")


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _print_json(payload: object) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(text)


def _normalize_round_id(round_id: str) -> str:
    value = round_id.strip().upper()
    if value not in ROUND_ORDER:
        raise ValueError(f"unsupported round_id: {round_id}")
    return value


def _diagnoses_for_mode(diagnosis_mode: str) -> dict[str, str]:
    mode = diagnosis_mode.strip().lower()
    if mode not in DIAGNOSIS_MODES:
        raise ValueError(f"unsupported diagnosis_mode: {diagnosis_mode}")
    return DIAGNOSIS_MODES[mode]


def _default_replay_dir(project_root: Path) -> Path:
    return project_root / "outputs" / "step3_reasoning_replay_v1"


def _default_out_dir(project_root: Path, round_id: str, output_dir: str | Path | None = None) -> Path:
    replay_dir = Path(output_dir) if output_dir is not None else _default_replay_dir(project_root)
    return replay_dir / "rounds" / round_id


def _load_kg(kg_dir: Path) -> tuple[list[dict], list[dict]]:
    nodes = _read_json(kg_dir / "kg_nodes.json")
    edges = _read_json(kg_dir / "kg_edges.json")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError(f"invalid KG payload in {kg_dir}")
    return nodes, edges


def _nodes_by_id(nodes: list[dict]) -> dict[str, dict]:
    return {node["node_id"]: node for node in nodes}


def _edge_label(edge: dict, node_by_id: dict[str, dict]) -> str:
    src = node_by_id.get(edge["src"], {})
    dst = node_by_id.get(edge["dst"], {})
    return (
        f"{edge['relation']}: "
        f"{src.get('type', '?')} {src.get('label', edge['src'])} -> "
        f"{dst.get('type', '?')} {dst.get('label', edge['dst'])}"
    )


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _load_doi_titles(path: Path = DOI_METADATA_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    titles: dict[str, str] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            doi = (row.get("doi") or "").strip().lower()
            title = (row.get("title") or "").strip()
            if doi and title:
                titles[doi] = title
    return titles


def _ref_title(doc_id: str, paper: dict | None, doi_titles: dict[str, str]) -> str:
    props = (paper or {}).get("props")
    doi = props.get("doi") if isinstance(props, dict) else None
    if isinstance(doi, str) and doi.strip():
        title = doi_titles.get(doi.strip().lower())
        if title:
            return title
    label = (paper or {}).get("label")
    if isinstance(label, str) and label.strip() and label.strip().lower() != str(doi or "").strip().lower():
        return label.strip()
    return doc_id


def _has_real_ref_title(ref: dict) -> bool:
    title = str(ref.get("title") or "").strip().lower()
    doi = str(ref.get("doi") or "").strip().lower()
    doc_id = str(ref.get("doc_id") or "").strip().lower()
    return bool(title and title not in {doi, doc_id})


def _node_text(node: dict) -> str:
    props = node.get("props")
    prop_text = ""
    if isinstance(props, dict):
        prop_text = " ".join(str(value) for value in props.values() if value is not None)
    return f"{node.get('node_id', '')} {node.get('type', '')} {node.get('label', '')} {prop_text}".lower()


def _edge_text(edge: dict, node_by_id: dict[str, dict]) -> str:
    return " ".join(
        [
            str(edge.get("relation", "")),
            _node_text(node_by_id.get(edge.get("src"), {})),
            _node_text(node_by_id.get(edge.get("dst"), {})),
            str(edge.get("source_doc_id") or ""),
            str(edge.get("source_chunk_id") or ""),
        ]
    ).lower()


def _evidence_counts(payload: object) -> dict[str, int]:
    text = json.dumps(payload, ensure_ascii=False).lower()
    corr_patterns = (
        r"\bcorr\b",
        r"\bco reduction\b",
        r"\bco electroreduction\b",
        r"\bcarbon monoxide reduction\b",
        r"\bco electrolysis\b",
        r"\bco-to-c2\+\b",
        r"\bco-to-acetate\b",
    )
    co2_patterns = (
        r"\bco2rr\b",
        r"\bco2 reduction\b",
        r"\bcarbon dioxide reduction\b",
        r"\bco2 feed\b",
        r"\bcarbon dioxide\b",
        r"\bco2\b",
    )
    return {
        "corr_terms": sum(len(re.findall(pattern, text)) for pattern in corr_patterns),
        "co2rr_terms": sum(len(re.findall(pattern, text)) for pattern in co2_patterns),
    }


def _diagnosis_query_terms(last_diagnosis: str) -> list[str]:
    terms = [last_diagnosis.lower()]
    for source, expansions in DIAGNOSIS_TERM_LEXICON.items():
        if source in last_diagnosis:
            terms.extend(term.lower() for term in expansions)
    terms.extend(token.lower() for token in re.findall(r"[A-Za-z0-9+@-]{2,}", last_diagnosis))
    return list(dict.fromkeys(term for term in terms if term.strip()))


def _retrieval_component_anchor_terms(round_id: str) -> list[str]:
    return [term.lower() for term in RETRIEVAL_COMPONENT_ANCHOR_TERMS.get(round_id, ()) if term.strip()]


def _edge_key(edge: dict) -> tuple:
    return (edge.get("src"), edge.get("dst"), edge.get("relation"), edge.get("source_doc_id"), edge.get("source_chunk_id"))


def _r7_chain_ring(node: dict) -> list[str]:
    text = _node_text(node)
    rings: list[str] = []
    node_type = node.get("type")
    if node_type == "Gas Feed" and "co2" not in text and "carbon dioxide" not in text and re.search(r"\bco\b|carbon monoxide|co gas|co feed", text):
        rings.append("CO feed")
    if re.search(r"\bcorr\b|\bco reduction\b|co electroreduction|carbon monoxide reduction|\bco electrolysis\b", text):
        rings.append("CORR/CO reduction")
    if (
        node_type == "Cathode"
        and re.search(r"\bcu\b|copper", text)
        and any(term in text for term in ("carbon paper", "carbon fiber paper", "carbon-paper", "gdl", "gas diffusion layer"))
    ):
        rings.append("Cu@carbon-paper cathode")
    if (
        node_type in {"Anode", "Reactor"}
        and re.search(r"\bpt\b|platinum|pt@", text)
        and ("ptl" in text or "porous transport layer" in text)
    ):
        rings.append("Pt@PTL anode")
    if node_type == "Separator" and "ptfe" in text and any(term in text for term in ("diaphragm", "membrane", "separator", "porous")):
        rings.append("porous PTFE diaphragm")
    if node_type == "Performance" and any(
        term in text
        for term in ("stable", "stability", "durability", "current density", "faradaic", "fe", "selectivity", "c2", "ethylene", "acetate", "performance")
    ):
        rings.append("stability/performance")
    return rings


def _incident_edge_map(edges: list[dict]) -> dict[str, list[dict]]:
    incident: dict[str, list[dict]] = {}
    for edge in edges:
        incident.setdefault(edge["src"], []).append(edge)
        incident.setdefault(edge["dst"], []).append(edge)
    return incident


def _other_edge_endpoint(edge: dict, node_id: str) -> str | None:
    if edge.get("src") == node_id:
        return edge.get("dst")
    if edge.get("dst") == node_id:
        return edge.get("src")
    return None


def _find_chain_path(start_ids: set[str], goal_ids: set[str], incident: dict[str, list[dict]], max_hops: int = 3) -> list[dict]:
    queue: list[tuple[str, list[dict]]] = [(node_id, []) for node_id in sorted(start_ids)]
    seen = set(start_ids)
    while queue:
        current, path = queue.pop(0)
        if current in goal_ids and path:
            return path
        if len(path) >= max_hops:
            continue
        for edge in incident.get(current, []):
            other = _other_edge_endpoint(edge, current)
            if not other or other in seen:
                continue
            seen.add(other)
            queue.append((other, [*path, edge]))
    return []


def _complete_r7_chain_subgraph(subgraph: dict, nodes: list[dict], edges: list[dict], node_by_id: dict[str, dict], max_edges: int = 80) -> dict:
    ring_to_ids: dict[str, set[str]] = {}
    for node in nodes:
        for ring in _r7_chain_ring(node):
            ring_to_ids.setdefault(ring, set()).add(node["node_id"])

    incident = _incident_edge_map(edges)
    chain_pairs = [
        ("CO feed", "CORR/CO reduction"),
        ("CORR/CO reduction", "Cu@carbon-paper cathode"),
        ("CORR/CO reduction", "Pt@PTL anode"),
        ("CORR/CO reduction", "porous PTFE diaphragm"),
        ("Cu@carbon-paper cathode", "stability/performance"),
        ("Pt@PTL anode", "stability/performance"),
        ("porous PTFE diaphragm", "stability/performance"),
        ("CO feed", "stability/performance"),
    ]

    required_edges: dict[tuple, dict] = {}
    path_status: list[dict] = []
    original_edge_keys = {_edge_key(edge) for edge in subgraph["edges"]}
    for src_ring, dst_ring in chain_pairs:
        path = _find_chain_path(ring_to_ids.get(src_ring, set()), ring_to_ids.get(dst_ring, set()), incident)
        status = "not_found_in_kg_within_3_hops"
        if path:
            path_keys = [_edge_key(edge) for edge in path]
            in_context = all(key in original_edge_keys for key in path_keys)
            status = "connected_in_context" if in_context else "completed_from_kg"
            for edge in path:
                required_edges[_edge_key(edge)] = edge
        path_status.append({"from": src_ring, "to": dst_ring, "status": status, "path_edge_count": len(path)})

    # If a required ring exists in KG but still has no selected node, preserve one traceable incident edge.
    selected_node_ids = {node["node_id"] for node in subgraph["nodes"]}
    for ring, ids in ring_to_ids.items():
        if selected_node_ids.intersection(ids):
            continue
        for node_id in sorted(ids):
            incident_edges = incident.get(node_id, [])
            if incident_edges:
                required_edges[_edge_key(incident_edges[0])] = incident_edges[0]
                path_status.append({"from": ring, "to": "incident evidence", "status": "completed_from_kg", "path_edge_count": 1})
                break

    original_edges = list(subgraph["edges"])
    merged_edges: list[dict] = []
    seen_keys: set[tuple] = set()
    for edge in list(required_edges.values()) + original_edges:
        key = _edge_key(edge)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        merged_edges.append(edge)
    if len(merged_edges) > max_edges:
        required_keys = set(required_edges)
        required_part = [edge for edge in merged_edges if _edge_key(edge) in required_keys]
        filler = [edge for edge in merged_edges if _edge_key(edge) not in required_keys]
        merged_edges = [*required_part, *filler[: max_edges - len(required_part)]]

    node_ids = {edge["src"] for edge in merged_edges} | {edge["dst"] for edge in merged_edges} | selected_node_ids
    subgraph["edges"] = merged_edges
    subgraph["nodes"] = [node_by_id[node_id] for node_id in sorted(node_ids) if node_id in node_by_id]
    return {
        "path_status": path_status,
        "required_edges_added": sum(1 for key in required_edges if key not in original_edge_keys),
        "required_edges_total": len(required_edges),
    }


def _edge_sort_key(edge: dict) -> tuple:
    return (
        edge.get("_hop", 99),
        str(edge.get("relation") or ""),
        str(edge.get("source_doc_id") or ""),
        str(edge.get("src") or ""),
        str(edge.get("dst") or ""),
        str(edge.get("source_chunk_id") or ""),
    )


def _copy_edge_with_hop(edge: dict, hop: int) -> dict:
    copied = dict(edge)
    copied["_hop"] = min(hop, int(copied.get("_hop", hop)))
    return copied


def _strip_internal_edge_fields(edge: dict) -> dict:
    return {key: value for key, value in edge.items() if not key.startswith("_")}


def _incident_edges(edges: list[dict]) -> dict[str, list[dict]]:
    incident: dict[str, list[dict]] = {}
    for edge in edges:
        incident.setdefault(edge["src"], []).append(edge)
        incident.setdefault(edge["dst"], []).append(edge)
    return incident


def _other_endpoint(edge: dict, node_id: str) -> str | None:
    if edge.get("src") == node_id:
        return edge.get("dst")
    if edge.get("dst") == node_id:
        return edge.get("src")
    return None


def _chain_edges(seed_ids: set[str], edges: list[dict]) -> tuple[list[dict], dict[str, int]]:
    incident = _incident_edges(edges)
    keyed: dict[tuple, dict] = {}
    first_hop_neighbors: set[str] = set()
    for seed_id in seed_ids:
        for edge in incident.get(seed_id, []):
            key = _edge_key(edge)
            keyed[key] = _copy_edge_with_hop(edge, 1)
            other = _other_endpoint(edge, seed_id)
            if other:
                first_hop_neighbors.add(other)
    one_hop_count = len(keyed)
    for node_id in first_hop_neighbors:
        for edge in incident.get(node_id, []):
            key = _edge_key(edge)
            if key in keyed:
                keyed[key]["_hop"] = min(int(keyed[key].get("_hop", 2)), 2)
            else:
                keyed[key] = _copy_edge_with_hop(edge, 2)
    return list(keyed.values()), {
        "one_hop_edges": one_hop_count,
        "two_hop_edges": len(keyed) - one_hop_count,
        "candidate_edges": len(keyed),
    }


def _balanced_edge_subset(edges: list[dict], max_edges: int = 80) -> list[dict]:
    if len(edges) <= max_edges:
        return [_strip_internal_edge_fields(edge) for edge in sorted(edges, key=_edge_sort_key)]

    groups: dict[str, list[dict]] = {}
    for edge in _spread_edges(edges):
        groups.setdefault(str(edge.get("relation") or "unknown"), []).append(edge)

    selected: list[dict] = []
    selected_keys: set[tuple] = set()
    seen_docs_by_relation: set[tuple[str, str]] = set()
    seen_nodes_by_relation: set[tuple[str, str]] = set()

    relation_names = sorted(groups)
    while len(selected) < max_edges:
        progressed = False
        for relation in relation_names:
            for edge in groups[relation]:
                key = _edge_key(edge)
                if key in selected_keys:
                    continue
                node_keys = ((relation, str(edge.get("src") or "")), (relation, str(edge.get("dst") or "")))
                if all(node_key in seen_nodes_by_relation for node_key in node_keys):
                    continue
                doc_key = (relation, str(edge.get("source_doc_id") or ""))
                if doc_key in seen_docs_by_relation:
                    continue
                selected.append(edge)
                selected_keys.add(key)
                seen_docs_by_relation.add(doc_key)
                seen_nodes_by_relation.update(node_keys)
                progressed = True
                break
            if len(selected) >= max_edges:
                break
        if not progressed:
            break

    if len(selected) < max_edges:
        for edge in _spread_edges(edges):
            key = _edge_key(edge)
            if key in selected_keys:
                continue
            selected.append(edge)
            selected_keys.add(key)
            if len(selected) >= max_edges:
                break

    return [_strip_internal_edge_fields(edge) for edge in selected]


def _spread_edges(edges: list[dict]) -> list[dict]:
    ordered = sorted(edges, key=_edge_sort_key)
    if len(ordered) <= 2:
        return ordered
    left = 0
    right = len(ordered) - 1
    spread: list[dict] = []
    while left <= right:
        spread.append(ordered[left])
        if left != right:
            spread.append(ordered[right])
        left += 1
        right -= 1
    return spread


def _edge_transport_dimensions(edge: dict, node_by_id: dict[str, dict]) -> list[str]:
    text = _edge_text(edge, node_by_id)
    return [
        dimension
        for dimension, terms in TRANSPORT_DIMENSIONS.items()
        if any(term.lower() in text for term in terms)
    ]


def _transport_dimension_edge_subset(
    edges: list[dict],
    all_edges: list[dict],
    node_by_id: dict[str, dict],
    max_edges: int = 80,
    per_dimension: int = 10,
) -> tuple[list[dict], dict[str, dict[str, int]]]:
    dimension_candidates: dict[str, list[dict]] = {dimension: [] for dimension in TRANSPORT_DIMENSIONS}
    global_dimension_candidates: dict[str, list[dict]] = {dimension: [] for dimension in TRANSPORT_DIMENSIONS}
    for edge in edges:
        for dimension in _edge_transport_dimensions(edge, node_by_id):
            dimension_candidates[dimension].append(edge)
    edge_keys = {_edge_key(edge) for edge in edges}
    for edge in all_edges:
        for dimension in _edge_transport_dimensions(edge, node_by_id):
            if _edge_key(edge) not in edge_keys:
                global_dimension_candidates[dimension].append(edge)

    selected: list[dict] = []
    selected_keys: set[tuple] = set()
    quota = max(1, min(per_dimension, max_edges))
    local_quota = max(1, quota // 2)
    for dimension in TRANSPORT_DIMENSIONS:
        dim_selected = 0
        for candidates, limit in (
            (dimension_candidates[dimension], local_quota),
            (global_dimension_candidates[dimension], quota - local_quota),
            (dimension_candidates[dimension] + global_dimension_candidates[dimension], quota),
        ):
            if dim_selected >= quota:
                break
            remaining = min(limit, quota - dim_selected)
            if remaining <= 0:
                continue
            for edge in _balanced_edge_subset(candidates, max_edges=remaining):
                key = _edge_key(edge)
                if key in selected_keys:
                    continue
                selected.append(edge)
                selected_keys.add(key)
                dim_selected += 1
                if len(selected) >= max_edges or dim_selected >= quota:
                    break
            if len(selected) >= max_edges:
                break
        if len(selected) >= max_edges:
            break

    if len(selected) < max_edges:
        for edge in _balanced_edge_subset(edges, max_edges=max_edges):
            key = _edge_key(edge)
            if key in selected_keys:
                continue
            selected.append(edge)
            selected_keys.add(key)
            if len(selected) >= max_edges:
                break

    selected_dimensions: dict[str, int] = {dimension: 0 for dimension in TRANSPORT_DIMENSIONS}
    for edge in selected:
        for dimension in _edge_transport_dimensions(edge, node_by_id):
            selected_dimensions[dimension] += 1

    counts = {
        dimension: {
            "candidate_edges": len(dimension_candidates[dimension]),
            "global_candidate_edges": len(global_dimension_candidates[dimension]),
            "selected_edges": selected_dimensions[dimension],
        }
        for dimension in TRANSPORT_DIMENSIONS
    }
    counts["_total"] = {
        "candidate_edges": len(edges),
        "selected_edges": len(selected),
    }
    return selected, counts


def fetch_reasoning_context(kg_dir: str | Path, round_id: str, last_diagnosis: str) -> dict:
    round_id = _normalize_round_id(round_id)
    kg_path = Path(kg_dir)
    nodes, edges = _load_kg(kg_path)
    node_by_id = _nodes_by_id(nodes)
    doi_titles = _load_doi_titles()

    query_terms = _diagnosis_query_terms(last_diagnosis)
    anchor_terms = _retrieval_component_anchor_terms(round_id)
    subgraph, retrieval_meta = reasoning_retrieval.ego_graph_subgraph(
        nodes,
        edges,
        node_by_id,
        diagnosis=last_diagnosis,
        query_terms=query_terms,
        anchor_terms=anchor_terms,
        transport_dimensions=TRANSPORT_DIMENSIONS,
        max_edges=80,
    )
    if round_id == "R7":
        retrieval_meta["chain_completion"] = _complete_r7_chain_subgraph(subgraph, nodes, edges, node_by_id, max_edges=80)
    edge_subset = subgraph["edges"]

    refs = []
    seen_docs: set[str] = set()
    for edge in edge_subset:
        doc_id = edge.get("source_doc_id")
        if not doc_id or doc_id in seen_docs:
            continue
        seen_docs.add(doc_id)
        paper = node_by_id.get(f"paper:{doc_id}")
        ref = {
            "doc_id": doc_id,
            "doi": (paper or {}).get("props", {}).get("doi") if isinstance((paper or {}).get("props"), dict) else None,
            "title": _ref_title(doc_id, paper, doi_titles),
        }
        if _has_real_ref_title(ref):
            refs.append(ref)
    if len(refs) < 6:
        for node in nodes:
            if node.get("type") != "Paper":
                continue
            props = node.get("props") or {}
            if not isinstance(props, dict):
                continue
            doc_id = props.get("doc_id")
            if not doc_id or doc_id in seen_docs:
                continue
            ref = {"doc_id": doc_id, "doi": props.get("doi"), "title": _ref_title(doc_id, node, doi_titles)}
            if not _has_real_ref_title(ref):
                continue
            seen_docs.add(doc_id)
            refs.append(ref)
            if len(refs) >= 6:
                break

    evidence_counts = _evidence_counts(subgraph)
    return {
        "subgraph": subgraph,
        "refs": refs,
        "prev_failures": [last_diagnosis],
        "seed_ids": retrieval_meta.get("anchor_ids", []),
        "seed_counts": {
            "algorithm": retrieval_meta.get("algorithm"),
            "anchor_selection": retrieval_meta.get("anchor_selection"),
            "anchors_by_type": retrieval_meta.get("anchors_by_type"),
            "role_types": retrieval_meta.get("role_types"),
            "total": retrieval_meta.get("anchor_count", 0),
        },
        "retrieval": retrieval_meta,
        "chain_counts": retrieval_meta.get("chain_counts", {}),
        "transport_dimensions": TRANSPORT_DIMENSIONS,
        "transport_dimension_counts": retrieval_meta.get("transport_dimension_counts", {}),
        "reaction_system_counts": {
            "preferred": retrieval_meta.get("preferred_reaction_system"),
            "candidate": retrieval_meta.get("candidate_reaction_system_counts", {}),
            "selected": retrieval_meta.get("selected_reaction_system_counts", {}),
            "selection": retrieval_meta.get("reaction_system_selection"),
        },
        "evidence_counts": evidence_counts,
    }


def _score_recommendation(round_id: str) -> float:
    idx = ROUND_ORDER.index(round_id)
    base = 100.0 - idx * 7.5
    penalties = {
        "R1": 18.0,
        "R2": 22.0,
        "R3": 14.0,
        "R4": 12.0,
        "R5": 10.0,
        "R6": 8.0,
        "R7": 6.0,
    }
    return round(base - penalties[round_id], 2)


def _build_recommendation(round_id: str, ctx: dict) -> ReactorRecommendation:
    full_refs = list(ctx["refs"])
    if len(full_refs) < 3:
        for node in ctx["subgraph"]["nodes"]:
            if node.get("type") != "Paper":
                continue
            doc_id = (node.get("props") or {}).get("doc_id")
            if not doc_id or any(ref["doc_id"] == doc_id for ref in full_refs):
                continue
            full_refs.append(
                {
                    "doc_id": doc_id,
                    "doi": (node.get("props") or {}).get("doi"),
                    "title": _ref_title(doc_id, node, _load_doi_titles()),
                }
            )
            if len(full_refs) >= 3:
                break
    if len(full_refs) < 3:
        raise ValueError(f"not enough literature refs for {round_id}: {len(full_refs)}")

    system = (
        "You are a reactor evolution reasoning engine. Use KG evidence and the provided diagnosis to argue for the next reactor structure.\n"
        "Do not invent a new research direction. Do not claim one-step discovery of the final system. Use only the provided evidence and refs.\n"
        "All causal claims must be grounded in the KG subgraph or the provided literature refs.\n"
        "Convert material choices into transport-path design. Explain how the proposed structure affects six transport functions: "
        "ion transport, water management, gas access, cation availability, ohmic loss, and mechanical stability. "
        "For each function, state the evidence-backed benefit or risk when the KG context supports it.\n"
        "Keep single-variable changes. design_change must contain 1 or 2 items only; combine details into one item if needed. "
        "Keep terminology compliant with the redline rules: gas-aerosol-solid / gas-liquid-solid contacting, "
        "AEM transmits anions not K+, PTFE is a porous diaphragm/separator, and R7 is a gradual convergence not a one-step invention.\n"
        "Use the supplied literature_refs exactly where possible, including their titles; do not replace titles with DOI strings.\n"
        "Output a strict JSON object matching the ReactorRecommendation schema."
    )
    user = json.dumps(
        {
            "round_id": round_id,
            "prev_failure_mode": ctx["prev_failures"],
            "diagnosis": ctx["prev_failures"],
            "kg_subgraph": {
                "nodes": ctx["subgraph"]["nodes"],
                "edges": ctx["subgraph"]["edges"],
            },
            "literature_refs": full_refs[:6],
            "evidence_counts": ctx.get("evidence_counts", {}),
            "seed_counts": ctx.get("seed_counts", {}),
            "chain_counts": ctx.get("chain_counts", {}),
            "transport_dimensions": ctx.get("transport_dimensions", {}),
            "transport_dimension_counts": ctx.get("transport_dimension_counts", {}),
            "max_design_changes": 2,
            "must_preserve": ["single-variable priority", "traceable evidence", "min 3 real literature refs"],
            "required_outputs": list(ReactorRecommendation.model_fields),
        },
        ensure_ascii=False,
    )
    recommendation = llm_client.call(role=DEFAULT_REASONING_ROLE, system=system, user=user, schema=ReactorRecommendation)
    refs_by_doc = {ref["doc_id"]: ref for ref in full_refs if ref.get("doc_id")}
    for ref in recommendation.literature_refs:
        source_ref = refs_by_doc.get(ref.doc_id)
        if not source_ref:
            continue
        source_doi = source_ref.get("doi")
        source_title = source_ref.get("title")
        if source_doi and not ref.doi:
            ref.doi = source_doi
        if source_title and ref.title.strip().lower() in {str(ref.doi or "").strip().lower(), ref.doc_id.lower()}:
            ref.title = source_title
    if recommendation.round_id != round_id:
        raise ValueError(f"mismatched round_id from reasoning model: {recommendation.round_id} != {round_id}")
    if not recommendation.score:
        recommendation.score = _score_recommendation(round_id)
    return recommendation


def _recommendation_text(recommendation: ReactorRecommendation) -> str:
    fields = [
        recommendation.primary_bottleneck,
        recommendation.hypothesis,
        recommendation.new_architecture,
        recommendation.rationale,
        recommendation.expected_improvement,
        recommendation.go_no_go,
        *recommendation.design_change,
        *recommendation.key_risks,
        *recommendation.min_experiment,
        *recommendation.discriminating_test,
        *recommendation.diagnostic_trigger,
    ]
    return " ".join(fields).lower()


def _feed_source_text(recommendation: ReactorRecommendation) -> str:
    fields = [
        recommendation.new_architecture,
        recommendation.hypothesis,
        *recommendation.design_change,
        *recommendation.min_experiment,
        *recommendation.discriminating_test,
    ]
    return " ".join(fields).lower()


def _infer_feeds(recommendation: ReactorRecommendation) -> tuple[list[str], list[str]]:
    text = _feed_source_text(recommendation)
    cathode_feed: list[str] = []
    anode_feed: list[str] = []
    if re.search(r"\bco\s*\+\s*h2\b", text):
        cathode_feed.append("CO+H2")
    elif re.search(r"(cathode feed|feed(?:ing)?).{0,40}\bco2\b|\bco2\b.{0,40}(cathode feed|feed)", text) or "co2 mea" in text:
        cathode_feed.append("CO2")
    elif "corr" in text or "co reduction" in text or "co electroreduction" in text or "carbon monoxide reduction" in text:
        cathode_feed.append("CO")
    if "koh aerosol" in text or "koh spray" in text:
        if any(side in text for side in ("cathode-side aerosol", "cathode aerosol", "cathode feed")):
            cathode_feed.append("KOH aerosol")
        anode_feed.append("KOH aerosol")
    if "hor" in text or re.search(r"\bh2\b", text):
        anode_feed.insert(0, "H2")
    if not cathode_feed:
        cathode_feed.append("not specified")
    if not anode_feed:
        anode_feed.append("not specified")
    return list(dict.fromkeys(cathode_feed)), list(dict.fromkeys(anode_feed))


def _gas_params(cathode_feed: list[str], anode_feed: list[str], use_koh_spray: bool) -> dict[str, str]:
    cathode = " / ".join(cathode_feed)
    anode = " / ".join(anode_feed)
    params = {
        "cathode_flow": f"10-50 sccm, feed from generated recommendation: {cathode}",
        "anode_flow": f"10-50 sccm, feed from generated recommendation: {anode}",
        "pressure": "near ambient, balanced across compartments",
    }
    if use_koh_spray:
        params["spray"] = "1 M KOH aerosol, controlled droplet loading"
    return params


def _infer_layers(recommendation: ReactorRecommendation) -> list[BuildLayer]:
    text = _recommendation_text(recommendation)
    layers: list[tuple[str, str]] = []
    if any(term in text for term in ("cathode", "gde", "gas-diffusion", "cu", "carbon paper")):
        material_terms = [term for term in ("Cu", "carbon paper", "GDE", "gas-diffusion electrode") if term.lower() in text]
        layers.append(("cathode", ", ".join(material_terms) if material_terms else "described in recommendation"))
    if any(term in text for term in ("interlayer", "electrolyte", "koh", "solid electrolyte", "liquid electrolyte")):
        material_terms = [term for term in ("1 M KOH", "liquid electrolyte", "solid electrolyte", "interlayer") if term.lower() in text]
        layers.append(("electrolyte/interlayer", ", ".join(material_terms) if material_terms else "described in recommendation"))
    if any(term in text for term in ("separator", "diaphragm", "membrane", "aem", "ptfe")):
        material_terms = [term for term in ("porous PTFE", "PTFE", "diaphragm", "separator", "AEM", "membrane") if term.lower() in text]
        layers.append(("separator", ", ".join(material_terms) if material_terms else "described in recommendation"))
    if any(term in text for term in ("anode", "ptl", "pt@", "hor", "h2")):
        material_terms = [term for term in ("Pt@PTL", "PTL", "Pt", "HOR", "anode") if term.lower() in text]
        layers.append(("anode", ", ".join(material_terms) if material_terms else "described in recommendation"))
    if not layers:
        layers.append(("reactor", recommendation.new_architecture or "not specified"))
    return [
        BuildLayer(
            order=idx,
            component=component,
            material=material,
            thickness="not specified",
            active_area="not specified",
        )
        for idx, (component, material) in enumerate(layers, start=1)
    ]


def build_build_sheet(round_id: str, project_root: str | Path, recommendation: ReactorRecommendation) -> BuildSheet:
    round_id = _normalize_round_id(round_id)
    _ = Path(project_root)
    cathode_feed, anode_feed = _infer_feeds(recommendation)
    text = _recommendation_text(recommendation)
    use_koh_spray = "koh aerosol" in text or "koh spray" in text or ("spray" in text and "koh" in text)
    prewetting = ["prewetting described in recommendation"] if "prewet" in text or "wet" in text or "humidified" in text else ["not specified"]
    safety = ["standard electrochemical cell safety checks"]
    if any(feed == "CO" or feed == "CO+H2" for feed in cathode_feed):
        safety.append("CO ventilation")
    if "H2" in anode_feed or any(feed == "CO+H2" for feed in cathode_feed):
        safety.append("H2 leak check")
    return BuildSheet(
        round_id=round_id,
        layers=_infer_layers(recommendation),
        cathode_feed=cathode_feed,
        anode_feed=anode_feed,
        use_koh_spray=use_koh_spray,
        prewetting=prewetting,
        gas_params=_gas_params(cathode_feed, anode_feed, use_koh_spray),
        gasket_and_clamping=["not specified by recommendation"],
        test_plan=recommendation.min_experiment or ["not specified"],
        teardown_photo_points=["not specified by recommendation"],
        safety_checks=list(dict.fromkeys(safety)),
        notes=recommendation.new_architecture,
    )


def _render_memo(recommendation: ReactorRecommendation, context: dict) -> str:
    lines = [
        f"# D3 Recommendation Memo - {recommendation.round_id}",
        "",
        f"Primary bottleneck: {recommendation.primary_bottleneck}",
        f"Hypothesis: {recommendation.hypothesis}",
        "",
        "## New Architecture",
        recommendation.new_architecture,
        "",
        "## Design Changes",
    ]
    lines.extend(f"- {item}" for item in recommendation.design_change)
    lines.extend(
        [
            "",
            "## Rationale",
            recommendation.rationale,
            "",
            "## Expected Improvement",
            recommendation.expected_improvement,
            "",
            "## Risks",
        ]
    )
    lines.extend(f"- {item}" for item in recommendation.key_risks)
    lines.extend(
        [
            "",
            "## Minimum Experiment",
        ]
    )
    lines.extend(f"- {item}" for item in recommendation.min_experiment)
    lines.extend(
        [
            "",
            "## Discriminating Test",
        ]
    )
    lines.extend(f"- {item}" for item in recommendation.discriminating_test)
    lines.extend(
        [
            "",
            "## Diagnostic Trigger",
        ]
    )
    lines.extend(f"- {item}" for item in recommendation.diagnostic_trigger)
    lines.extend(
        [
            "",
            f"Go/No-Go: {recommendation.go_no_go}",
            "",
            "## Literature",
        ]
    )
    for ref in recommendation.literature_refs:
        lines.append(f"- {ref.doc_id} | {ref.doi or ''} | {ref.title}")
    lines.extend(["", f"Score: {recommendation.score}", "", f"Referenced nodes: {len(context['subgraph']['nodes'])}", f"Referenced edges: {len(context['subgraph']['edges'])}"])
    return "\n".join(lines) + "\n"


def _render_build_sheet(build_sheet: BuildSheet) -> str:
    lines = [f"# D3 Build Sheet - {build_sheet.round_id}", ""]
    lines.append("## Layers")
    lines.append("| order | component | material | thickness | active area |")
    lines.append("|---:|---|---|---|---|")
    for layer in build_sheet.layers:
        lines.append(f"| {layer.order} | {layer.component} | {layer.material} | {layer.thickness} | {layer.active_area} |")
    lines.append("")
    sections = [
        ("Cathode Feed", build_sheet.cathode_feed),
        ("Anode Feed", build_sheet.anode_feed),
        ("Prewetting", build_sheet.prewetting),
        ("Gasket And Clamping", build_sheet.gasket_and_clamping),
        ("Test Plan", build_sheet.test_plan),
        ("Teardown Photo Points", build_sheet.teardown_photo_points),
        ("Safety Checks", build_sheet.safety_checks),
    ]
    lines.append(f"Use KOH spray: {build_sheet.use_koh_spray}")
    lines.append("")
    lines.append("## Gas Params")
    for key, value in build_sheet.gas_params.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    for title, items in sections:
        lines.append(f"## {title}")
        lines.extend(f"- {item}" for item in items)
        lines.append("")
    if build_sheet.notes:
        lines.append("## Notes")
        lines.append(build_sheet.notes)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def check_redlines(text: str) -> list[str]:
    lowered = text.lower()
    problems = []
    if "气固两相流" in text or "gas-solid two-phase flow" in lowered:
        problems.append("forbidden term: 气固两相流")
    if "aem 提供 k+" in lowered or "aem provides k+" in lowered:
        problems.append("forbidden term: AEM provides K+")
    ptfe_ixm_pattern = re.search(
        r"ptfe[- ]ion[- ]exchange membrane|"
        r"ptfe.{0,40}\b(is|as|acts as|serves as|used as|functions as)\b.{0,40}ion[- ]exchange membrane|"
        r"ion[- ]exchange membrane.{0,40}(made of|based on|using|from).{0,40}ptfe",
        lowered,
    )
    if ptfe_ixm_pattern:
        window = lowered[max(0, ptfe_ixm_pattern.start() - 80) : ptfe_ixm_pattern.end() + 80]
        if not re.search(r"(replace|replacing|replaced by|substitute|substituting|versus|instead of|rather than|not |does not|is not|isn't|non[- ]ion|not ion|not cation)", window):
            problems.append("forbidden term: PTFE as ion exchange membrane")
    one_step_r7_claim = re.search(r"(claim|discover|invent|found|create|created|generate|generated).{0,40}(r7|final).{0,40}(one[- ]step|single[- ]step)", lowered)
    one_step_r7_claim = one_step_r7_claim or re.search(r"(one[- ]step|single[- ]step).{0,40}(claim|discover|invent|found|create|created|generate|generated).{0,40}(r7|final)", lowered)
    if one_step_r7_claim:
        prefix = lowered[max(0, one_step_r7_claim.start() - 30) : one_step_r7_claim.start()]
        if any(marker in prefix for marker in ("without ", "not ", "rather than ", "instead of ")):
            one_step_r7_claim = None
    if "self-discovered" in lowered or one_step_r7_claim:
        problems.append("forbidden claim: one-step R7 discovery")
    return problems


def _validate_recommendation(recommendation: ReactorRecommendation, context: dict | None = None) -> list[str]:
    problems = []
    if len(recommendation.literature_refs) < 3:
        problems.append("literature_refs must be at least 3")
    if not recommendation.design_change:
        problems.append("design_change cannot be empty")
    if len(recommendation.design_change) > 2:
        problems.append("design_change must contain at most 2 key changes")
    if not recommendation.key_risks:
        problems.append("key_risks cannot be empty")
    if not recommendation.min_experiment:
        problems.append("min_experiment cannot be empty")
    if not recommendation.discriminating_test:
        problems.append("discriminating_test cannot be empty")
    if check_redlines(recommendation.hypothesis):
        problems.append("hypothesis violates redlines")
    if check_redlines(recommendation.new_architecture):
        problems.append("new_architecture violates redlines")
    if check_redlines(recommendation.rationale):
        problems.append("rationale violates redlines")
    if context is not None:
        context_refs = {ref["doc_id"]: ref for ref in context.get("refs", [])}
        valid_doc_ids = set(context_refs)
        valid_doc_ids |= {
            (node.get("props") or {}).get("doc_id")
            for node in context.get("subgraph", {}).get("nodes", [])
            if node.get("type") == "Paper" and isinstance(node.get("props"), dict)
        }
        valid_doc_ids.discard(None)
        bad_refs = [ref.doc_id for ref in recommendation.literature_refs if ref.doc_id not in valid_doc_ids]
        if bad_refs:
            problems.append(f"literature_refs not present in KG context: {bad_refs}")
        bad_dois = []
        bad_titles = []
        for ref in recommendation.literature_refs:
            expected = context_refs.get(ref.doc_id, {}).get("doi")
            if ref.doi and expected and ref.doi != expected:
                bad_dois.append(ref.doc_id)
            if ref.title.strip().lower() in {str(ref.doi or "").strip().lower(), ref.doc_id.lower()}:
                bad_titles.append(ref.doc_id)
        if bad_dois:
            problems.append(f"literature_refs DOI mismatch for KG context: {bad_dois}")
        if bad_titles:
            problems.append(f"literature_refs title missing or replaced by DOI/doc_id: {bad_titles}")
    return problems


def _write_run_config(
    out_dir: Path,
    round_id: str,
    kg_dir: Path,
    diagnosis: str,
    recommendation: ReactorRecommendation,
    build_sheet: BuildSheet,
    context: dict,
) -> None:
    config = Step3RunConfig(
        round_id=round_id,
        kg_dir=str(kg_dir),
        output_dir=str(out_dir),
        diagnosis=diagnosis,
        evidence_counts=context.get("evidence_counts"),
        seed_counts=context.get("seed_counts"),
        chain_counts=context.get("chain_counts"),
        transport_dimension_counts=context.get("transport_dimension_counts"),
        reaction_system_counts=context.get("reaction_system_counts"),
        selected_doc_ids=[ref.doc_id for ref in recommendation.literature_refs],
        model_role=DEFAULT_REASONING_ROLE,
        model_name=DEFAULT_REASONING_MODEL,
    )
    _write_json(out_dir / "run_config.json", config.model_dump(mode="json"))


def run_reasoning(
    round_id: str,
    project_root: str | Path,
    last_diagnosis: str,
    kg_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    max_validation_attempts: int = 3,
) -> ReactorRecommendation:
    round_id = _normalize_round_id(round_id)
    project_root = Path(project_root)
    kg_path = Path(kg_dir) if kg_dir is not None else project_root / "outputs" / "step2_causal_kg_run_ready_v2_normalized"
    out_dir = _default_out_dir(project_root, round_id, output_dir=output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    context = fetch_reasoning_context(kg_path, round_id, last_diagnosis)
    recommendation = None
    problems: list[str] = []
    for attempt in range(1, max_validation_attempts + 1):
        candidate = _build_recommendation(round_id, context)
        problems = _validate_recommendation(candidate, context)
        if not problems:
            recommendation = candidate
            break
    if recommendation is None:
        raise ValueError("recommendation validation failed:\n" + "\n".join(problems))

    build_sheet = build_build_sheet(round_id, project_root, recommendation)
    memo_text = _render_memo(recommendation, context)
    build_text = _render_build_sheet(build_sheet)

    _write_json(out_dir / "D3_memo.json", recommendation.model_dump(mode="json"))
    _write_text(out_dir / "D3_memo.md", memo_text)
    _write_json(out_dir / "D3_build_sheet.json", build_sheet.model_dump(mode="json"))
    _write_text(out_dir / "D3_build_sheet.md", build_text)
    _write_json(out_dir / "D3_context.json", context)
    _write_run_config(out_dir, round_id, kg_path, last_diagnosis, recommendation, build_sheet, context)
    return recommendation


def run_replay(
    project_root: str | Path,
    kg_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    diagnosis_mode: str = "brief",
) -> list[dict]:
    project_root = Path(project_root)
    kg_path = Path(kg_dir) if kg_dir is not None else project_root / "outputs" / "step2_causal_kg_run_ready_v2_normalized"
    replay_dir = Path(output_dir) if output_dir is not None else _default_replay_dir(project_root)
    diagnoses = _diagnoses_for_mode(diagnosis_mode)
    results = []
    for round_id in ROUND_ORDER:
        diagnosis = diagnoses[round_id]
        recommendation = run_reasoning(round_id, project_root, diagnosis, kg_dir=kg_path, output_dir=replay_dir)
        results.append(
            {
                "round_id": round_id,
                "diagnosis": diagnosis,
                "diagnosis_mode": diagnosis_mode,
                "new_architecture": recommendation.new_architecture,
                "primary_bottleneck": recommendation.primary_bottleneck,
                "score": recommendation.score,
            }
        )
    _write_json(replay_dir / "replay_summary.json", results)
    _write_quality_report(replay_dir, kg_path, results)
    return results


def _compare_taskbook_structure(round_id: str, agent_text: str) -> tuple[bool, dict[str, object]]:
    lowered = f" {agent_text.lower()} "
    requirement_groups = TASKBOOK_STRUCTURE_REQUIREMENTS[round_id]
    matched_groups = []
    missing_groups = []
    for group in requirement_groups:
        hits = [term for term in group if term.lower() in lowered]
        if hits:
            matched_groups.append(hits)
        else:
            missing_groups.append(list(group))
    return not missing_groups, {"matched_groups": matched_groups, "missing_groups": missing_groups}


def _compare_round_reasoning_target(round_id: str, agent_text: str) -> tuple[bool, dict[str, object]]:
    lowered = f" {agent_text.lower()} "
    target_groups = ROUND_REASONING_TARGETS[round_id]
    matched_groups = []
    missing_groups = []
    for group in target_groups:
        hits = [term for term in group if term.lower() in lowered]
        if hits:
            matched_groups.append(hits)
        else:
            missing_groups.append(list(group))
    return not missing_groups, {"matched_groups": matched_groups, "missing_groups": missing_groups}


def _diagnosis_no_structure_answer(diagnosis: str) -> tuple[bool, list[str]]:
    lowered = f" {diagnosis.lower()} "
    hits = [pattern for pattern in DIAGNOSIS_ANSWER_PATTERNS if re.search(pattern, lowered)]
    return not hits, hits


def _four_part_complete(memo: ReactorRecommendation) -> tuple[bool, dict[str, bool]]:
    parts = {
        "hypothesis": bool(memo.hypothesis.strip()),
        "design": bool(memo.new_architecture.strip()) and bool(memo.design_change),
        "risk": bool(memo.key_risks),
        "measurement_plan": bool(memo.min_experiment) and bool(memo.discriminating_test),
    }
    return all(parts.values()), parts


def _round_quality_row(round_dir: Path, result: dict) -> dict:
    round_id = result["round_id"]
    if not (round_dir / "D3_memo.json").exists() or not (round_dir / "D3_build_sheet.json").exists() or not (round_dir / "D3_context.json").exists():
        return {
            "round_id": round_id,
            "taskbook_structure": TASKBOOK_RECOMMENDED_STRUCTURES[round_id],
            "agent_structure": result.get("new_architecture", ""),
            "structure_match": None,
            "structure_match_notes": {},
            "reasoning_target_match": None,
            "reasoning_target_notes": {},
            "four_part_complete": None,
            "four_part_notes": {},
            "structure_terms_reference_match": None,
            "structure_terms_reference_notes": {},
            "diagnosis": result.get("diagnosis", ""),
            "diagnosis_mode": result.get("diagnosis_mode", "unknown"),
            "diagnosis_no_structure_answer": None,
            "diagnosis_answer_patterns": [],
            "redline_ok": None,
            "single_variable_ok": None,
            "refs_ok": None,
            "corr_terms": None,
            "co2rr_terms": None,
            "seed_counts": None,
            "chain_counts": None,
            "reaction_system_counts": None,
            "transport_dimension_counts": None,
            "cathode_feed": [],
            "anode_feed": [],
            "validation_problems": ["round files missing; quality row generated from replay summary only"],
            "redline_problems": [],
        }
    memo = ReactorRecommendation.model_validate(_read_json(round_dir / "D3_memo.json"))
    build = BuildSheet.model_validate(_read_json(round_dir / "D3_build_sheet.json"))
    context = _read_json(round_dir / "D3_context.json")
    memo_text = json.dumps(memo.model_dump(mode="json"), ensure_ascii=False)
    build_text = json.dumps(build.model_dump(mode="json"), ensure_ascii=False)
    redlines = check_redlines(memo_text + " " + build_text)
    validation = _validate_recommendation(memo, context if isinstance(context, dict) else None)
    generated_text = " ".join(
        [
            memo.primary_bottleneck,
            memo.hypothesis,
            memo.new_architecture,
            memo.rationale,
            memo.expected_improvement,
            memo.go_no_go,
            *memo.design_change,
            *memo.key_risks,
            *memo.min_experiment,
            *memo.discriminating_test,
            *memo.diagnostic_trigger,
        ]
    ).lower()
    reasoning_match, reasoning_notes = _compare_round_reasoning_target(round_id, generated_text)
    four_part_ok, four_part_notes = _four_part_complete(memo)
    structure_reference_match, structure_reference_notes = _compare_taskbook_structure(round_id, generated_text)
    diagnosis_text = str(result.get("diagnosis") or " ".join(memo.prev_failure_mode))
    diagnosis_ok, diagnosis_patterns = _diagnosis_no_structure_answer(diagnosis_text)
    title_ok = all(ref.title.strip().lower() not in {str(ref.doi or "").strip().lower(), ref.doc_id.lower()} for ref in memo.literature_refs)
    return {
        "round_id": round_id,
        "taskbook_structure": TASKBOOK_RECOMMENDED_STRUCTURES[round_id],
        "agent_structure": memo.new_architecture,
        "structure_match": reasoning_match and four_part_ok,
        "structure_match_notes": {"reasoning_target": reasoning_notes, "four_part": four_part_notes},
        "reasoning_target_match": reasoning_match,
        "reasoning_target_notes": reasoning_notes,
        "four_part_complete": four_part_ok,
        "four_part_notes": four_part_notes,
        "structure_terms_reference_match": structure_reference_match,
        "structure_terms_reference_notes": structure_reference_notes,
        "diagnosis": diagnosis_text,
        "diagnosis_mode": result.get("diagnosis_mode", "unknown"),
        "diagnosis_no_structure_answer": diagnosis_ok,
        "diagnosis_answer_patterns": diagnosis_patterns,
        "redline_ok": not redlines,
        "single_variable_ok": 1 <= len(memo.design_change) <= 2,
        "refs_ok": len(memo.literature_refs) >= 3 and title_ok,
        "corr_terms": (context or {}).get("evidence_counts", {}).get("corr_terms") if isinstance(context, dict) else None,
        "co2rr_terms": (context or {}).get("evidence_counts", {}).get("co2rr_terms") if isinstance(context, dict) else None,
        "seed_counts": (context or {}).get("seed_counts") if isinstance(context, dict) else None,
        "chain_counts": (context or {}).get("chain_counts") if isinstance(context, dict) else None,
        "reaction_system_counts": (context or {}).get("reaction_system_counts") if isinstance(context, dict) else None,
        "transport_dimension_counts": (context or {}).get("transport_dimension_counts") if isinstance(context, dict) else None,
        "cathode_feed": build.cathode_feed,
        "anode_feed": build.anode_feed,
        "validation_problems": validation,
        "redline_problems": redlines,
    }


def _write_quality_report(replay_dir: Path, kg_path: Path, results: list[dict]) -> None:
    rows = [_round_quality_row(replay_dir / "rounds" / result["round_id"], result) for result in results]
    lines = [
        "# Step3 Quality Report",
        "",
        f"- KG input: `{kg_path}`",
        f"- Output: `{replay_dir}`",
        f"- Rounds: {len(rows)}",
        f"- Structure match criterion: round diagnosis/next-logic semantic targets + hypothesis/design/risk/measurement-plan completeness.",
        f"- Structure-name terms are reported as a reference only, not as a pass/fail gate.",
        "",
        "## Taskbook Reasoning Comparison",
        "",
        "| round | diagnosis mode | diagnosis has no structure answer | diagnosis/logic match | four-part complete | structure match | structure-term reference | notes |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            "| {round_id} | {diagnosis_mode} | {diagnosis_no_structure_answer} | {reasoning_target_match} | {four_part_complete} | {structure_match} | {structure_terms_reference_match} | {structure_match_notes} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Diagnosis Inputs",
            "",
            "| round | mode | no structure answer | diagnosis |",
            "|---|---|---:|---|",
        ]
    )
    for row in rows:
        lines.append("| {round_id} | {diagnosis_mode} | {diagnosis_no_structure_answer} | {diagnosis} |".format(**row))
    lines.extend(
        [
            "",
            "## Structure Term Reference",
            "",
            "| round | taskbook recommended structure | agent structure | term reference notes |",
            "|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {round_id} | {taskbook_structure} | {agent_structure} | {structure_terms_reference_notes} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Evidence And QC",
            "",
            "| round | redline | single variable | refs | CORR terms | CO2RR terms | reaction systems | seed counts | chain counts | transport dimensions | cathode feed | anode feed |",
            "|---|---:|---:|---:|---:|---:|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append(
            "| {round_id} | {redline_ok} | {single_variable_ok} | {refs_ok} | {corr_terms} | {co2rr_terms} | {reaction_system_counts} | {seed_counts} | {chain_counts} | {transport_dimension_counts} | {cathode_feed} | {anode_feed} |".format(
                **row
            )
        )
    mismatches = [row for row in rows if row["structure_match"] is False]
    problems = [
        row
        for row in rows
        if row["validation_problems"]
        or row["redline_problems"]
        or row["refs_ok"] is False
        or row["diagnosis_no_structure_answer"] is False
    ]
    lines.extend(["", "## Structure Mismatches", ""])
    if not mismatches:
        lines.append("- None.")
    else:
        for row in mismatches:
            lines.append(f"- {row['round_id']}: {row['structure_match_notes']}")
    lines.extend(["", "## Problems", ""])
    if not problems:
        lines.append("- None.")
    else:
        for row in problems:
            lines.append(
                f"- {row['round_id']}: refs={row['refs_ok']} validation={row['validation_problems']} redline={row['redline_problems']} diagnosis_answer_patterns={row['diagnosis_answer_patterns']}"
            )
    _write_json(replay_dir / "quality_report.json", rows)
    _write_text(replay_dir / "STEP3_QUALITY_REPORT.md", "\n".join(lines) + "\n")


def recompute_quality_report(output_dir: str | Path, kg_dir: str | Path | None = None) -> list[dict]:
    replay_dir = Path(output_dir)
    results = []
    for round_dir in sorted((replay_dir / "rounds").glob("R*")):
        if not round_dir.is_dir() or not (round_dir / "D3_memo.json").exists():
            continue
        memo = ReactorRecommendation.model_validate(_read_json(round_dir / "D3_memo.json"))
        results.append(
            {
                "round_id": memo.round_id,
                "diagnosis": " ".join(memo.prev_failure_mode),
                "diagnosis_mode": "recomputed",
                "new_architecture": memo.new_architecture,
                "primary_bottleneck": memo.primary_bottleneck,
                "score": memo.score,
            }
        )
    if not results:
        raise ValueError(f"no existing Step3 round outputs found under {replay_dir / 'rounds'}")
    if kg_dir is not None:
        kg_path = Path(kg_dir)
    else:
        first_config = _read_json(replay_dir / "rounds" / results[0]["round_id"] / "run_config.json")
        kg_path = Path(first_config.get("kg_dir", ""))
    _write_json(replay_dir / "recomputed_quality_summary.json", results)
    _write_quality_report(replay_dir, kg_path, results)
    return results


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run Reactor Step 3 reasoning replay.")
    parser.add_argument("--project-root", default=str(Path.cwd()))
    parser.add_argument("--kg-dir")
    parser.add_argument("--out-dir", help="Step3 output directory. Defaults to outputs/step3_reasoning_replay_v1.")
    parser.add_argument("--round-id")
    parser.add_argument("--diagnosis")
    parser.add_argument("--replay", action="store_true")
    parser.add_argument("--quality-only", action="store_true", help="Recompute quality_report.json and STEP3_QUALITY_REPORT.md from existing round outputs without running the agent.")
    parser.add_argument("--diagnosis-mode", choices=sorted(DIAGNOSIS_MODES), default="brief", help="Diagnosis input set for --replay.")
    args = parser.parse_args()

    if args.quality_only:
        results = recompute_quality_report(args.out_dir or _default_replay_dir(Path(args.project_root)), kg_dir=args.kg_dir)
        _print_json(results)
        return

    if args.replay:
        results = run_replay(args.project_root, kg_dir=args.kg_dir, output_dir=args.out_dir, diagnosis_mode=args.diagnosis_mode)
        _print_json(results)
        return

    if not args.round_id or not args.diagnosis:
        raise SystemExit("--round-id and --diagnosis are required unless --replay is used")

    recommendation = run_reasoning(args.round_id, args.project_root, args.diagnosis, kg_dir=args.kg_dir, output_dir=args.out_dir)
    _print_json(recommendation.model_dump(mode="json"))


if __name__ == "__main__":
    main()
