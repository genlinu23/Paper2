from __future__ import annotations

import math
import re
from collections import Counter, defaultdict


MAX_EDGES = 80
EGO_ANCHORS = 24
EGO_TYPE_QUOTA = 3
EGO_ROLE_TYPE_QUOTA = 6
TOKEN_RE = re.compile(r"[a-z0-9+@-]{2,}")
REACTION_SYSTEMS = ("CO2RR", "CORR", "transferable", "other_reaction", "unknown")
CORR_QUERY_RE = re.compile(
    r"\bcorr\b|\bco reduction\b|\bco electroreduction\b|\bcarbon monoxide\b|\bcarbon monoxide reduction\b|\bco electrolysis\b|\bco feed\b|\bco gas\b"
)
CO2RR_QUERY_RE = re.compile(r"\bco2rr\b|\bco2\b|\bco₂\b|\bcarbon dioxide\b|\bco2 reduction\b|\bcarbon dioxide reduction\b")


def node_text(node: dict) -> str:
    props = node.get("props")
    prop_text = ""
    if isinstance(props, dict):
        prop_text = " ".join(str(value) for value in props.values() if value is not None)
    return f"{node.get('node_id', '')} {node.get('type', '')} {node.get('label', '')} {prop_text}".lower()


def edge_text(edge: dict, node_by_id: dict[str, dict]) -> str:
    return " ".join(
        [
            str(edge.get("relation", "")),
            str(edge.get("reaction_system") or ""),
            node_text(node_by_id.get(edge.get("src"), {})),
            node_text(node_by_id.get(edge.get("dst"), {})),
            str(edge.get("source_doc_id") or ""),
            str(edge.get("source_chunk_id") or ""),
        ]
    ).lower()


def evidence_counts(payload: object) -> dict[str, int]:
    import json

    text = json.dumps(payload, ensure_ascii=False).lower()
    corr_terms = ("corr", "co reduction", "co electroreduction", "carbon monoxide reduction", "co electrolysis", "co-to-c2+", "co-to-acetate")
    co2_terms = ("co2rr", "co2 reduction", "carbon dioxide reduction", "co2 feed", "carbon dioxide", "co2")
    return {
        "corr_terms": sum(text.count(term) for term in corr_terms),
        "co2rr_terms": sum(text.count(term) for term in co2_terms),
    }


def preferred_reaction_system(query_terms: list[str], diagnosis: str = "") -> str | None:
    text = " ".join([diagnosis, *query_terms]).lower()
    corr = bool(CORR_QUERY_RE.search(text))
    co2rr = bool(CO2RR_QUERY_RE.search(text))
    if corr and not co2rr:
        return "CORR"
    if co2rr and not corr:
        return "CO2RR"
    return None


def reaction_system_priority(edge: dict, preferred_system: str | None) -> int:
    system = edge.get("reaction_system") or "unknown"
    if preferred_system is None:
        if system == "transferable":
            return 2
        if system == "unknown":
            return 1
        return 0
    if system == preferred_system:
        return 4
    if system == "transferable":
        return 3
    if system == "unknown":
        return 2
    return 1


def reaction_system_counts(edges: list[dict]) -> dict[str, int]:
    counts = Counter(edge.get("reaction_system") or "MISSING" for edge in edges)
    return {system: counts.get(system, 0) for system in (*REACTION_SYSTEMS, "MISSING")}


def edge_key(edge: dict) -> tuple:
    return (edge.get("src"), edge.get("dst"), edge.get("relation"), edge.get("source_doc_id"), edge.get("source_chunk_id"))


def strip_internal_edge_fields(edge: dict) -> dict:
    return {key: value for key, value in edge.items() if not key.startswith("_")}


def dedupe_edges(edges: list[dict]) -> list[dict]:
    keyed: dict[tuple, dict] = {}
    for edge in edges:
        keyed.setdefault(edge_key(edge), edge)
    return list(keyed.values())


def tokens(text: str) -> Counter[str]:
    return Counter(TOKEN_RE.findall(text.lower()))


def cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(value * b.get(key, 0) for key, value in a.items())
    if not dot:
        return 0.0
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def anchor_query_terms(query_terms: list[str]) -> list[str]:
    joined = " ".join(term.lower() for term in query_terms)
    extra: list[str] = []
    if any(term in joined for term in ("separator", "membrane", "separation", "physical separation", "ptfe")):
        extra.extend(["diaphragm", "porous diaphragm", "porous ptfe"])
    if any(term in joined for term in ("spray", "aerosol", "droplet")):
        extra.extend(["spray", "aerosol", "droplet"])
    if "ptl" in joined or "porous transport layer" in joined:
        extra.extend(["ptl", "porous transport layer"])
    return list(dict.fromkeys([*query_terms, *extra]))


def incident_edges(edges: list[dict]) -> dict[str, list[dict]]:
    incident: dict[str, list[dict]] = {}
    for edge in edges:
        incident.setdefault(edge["src"], []).append(edge)
        incident.setdefault(edge["dst"], []).append(edge)
    return incident


def other_endpoint(edge: dict, node_id: str) -> str | None:
    if edge.get("src") == node_id:
        return edge.get("dst")
    if edge.get("dst") == node_id:
        return edge.get("src")
    return None


def copy_edge_with_hop(edge: dict, hop: int) -> dict:
    copied = dict(edge)
    copied["_hop"] = min(hop, int(copied.get("_hop", hop)))
    return copied


def chain_edges(seed_ids: set[str], edges: list[dict]) -> tuple[list[dict], dict[str, int]]:
    incident = incident_edges(edges)
    keyed: dict[tuple, dict] = {}
    first_hop_neighbors: set[str] = set()
    for seed_id in seed_ids:
        for edge in incident.get(seed_id, []):
            key = edge_key(edge)
            keyed[key] = copy_edge_with_hop(edge, 1)
            other = other_endpoint(edge, seed_id)
            if other:
                first_hop_neighbors.add(other)
    one_hop_count = len(keyed)
    for node_id in first_hop_neighbors:
        for edge in incident.get(node_id, []):
            key = edge_key(edge)
            if key in keyed:
                keyed[key]["_hop"] = min(int(keyed[key].get("_hop", 2)), 2)
            else:
                keyed[key] = copy_edge_with_hop(edge, 2)
    return list(keyed.values()), {
        "one_hop_edges": one_hop_count,
        "two_hop_edges": len(keyed) - one_hop_count,
        "candidate_edges": len(keyed),
    }


def role_relevant_types(query_terms: list[str]) -> list[str]:
    query = " ".join(term.lower() for term in query_terms)
    role_types: list[str] = []
    if any(term in query for term in ("corr", "co reduction", "co electroreduction", "co feed", "co gas feed", "carbon monoxide")):
        role_types.extend(["Gas Feed", "Reactor", "Cathode", "Performance"])
    if any(term in query for term in ("separator", "membrane", "diaphragm", "separation", "ptfe")):
        role_types.extend(["Separator", "Reactor"])
    if any(term in query for term in ("spray", "aerosol", "gas", "h2o", "water", "droplet")):
        role_types.extend(["Gas Feed", "Operating Condition", "Reactor"])
    if any(term in query for term in ("koh", "k+", "cation", "electrolyte")):
        role_types.extend(["Electrolyte", "Operating Condition"])
    if any(term in query for term in ("ptl", "anode", "h2", "hor")):
        role_types.extend(["Anode", "Reactor"])
    if any(term in query for term in ("cathode", "carbon paper", "cu", "copper", "catalyst")):
        role_types.extend(["Cathode"])
    return list(dict.fromkeys(role_types))


def role_material_terms(query_terms: list[str]) -> tuple[set[str], set[str]]:
    joined = " ".join(term.lower() for term in query_terms)
    materials = {
        term
        for term in (
            "ptfe",
            "eptfe",
            "ptl",
            "koh",
            "k+",
            "h2o",
            "h2",
            "cu",
            "copper",
            "carbon paper",
            "co feed",
            "co gas feed",
            "co reduction",
            "co electroreduction",
            "carbon monoxide",
            "corr",
            "pt@ptl",
        )
        if term in joined
    }
    roles = {
        term
        for term in (
            "separator",
            "membrane",
            "diaphragm",
            "porous diaphragm",
            "porous ptfe",
            "spray",
            "aerosol",
            "gas feed",
            "electrolyte",
            "anode",
            "cathode",
            "ptl",
            "gas feed",
            "performance",
            "reactor",
        )
        if term in joined
    }
    return materials, roles


def score_nodes_by_type(nodes: list[dict], query_terms: list[str]) -> dict[str, list[tuple[int, int, int, str, str]]]:
    by_type: dict[str, list[tuple[int, int, int, str, str]]] = defaultdict(list)
    material_terms, role_terms = role_material_terms(query_terms)
    joined_query = " ".join(term.lower() for term in query_terms)
    for node in nodes:
        text = node_text(node)
        label_text = f"{node.get('node_id', '')} {node.get('label', '')}".lower()
        hits = sum(1 for term in query_terms if term.lower() in text)
        if not hits:
            continue
        exact_label_hits = sum(1 for term in query_terms if term.lower() in label_text)
        material_hits = sum(1 for term in material_terms if term in label_text)
        role_hits = sum(1 for term in role_terms if term in label_text)
        role_material_bonus = material_hits * 3 + role_hits
        if material_hits and role_hits:
            role_material_bonus += 5
        if "ptfe" in label_text and "diaphragm" in label_text:
            role_material_bonus += 35
        if "ptfe" in label_text and any(term in label_text for term in ("diaphragm", "porous")):
            role_material_bonus += 20
        if "ptfe" in label_text and "membrane" in label_text:
            role_material_bonus += 8
        if "ptfe" in label_text and any(term in label_text for term in ("catalyst", "cathode")) and node.get("type") != "Cathode":
            role_material_bonus -= 3
        if (
            node.get("type") == "Anode"
            and any(term in joined_query for term in ("pt@ptl", "ptl anode", "pt-ruo2", "titanium felt ptl"))
            and ("ptl" in label_text or "porous transport layer" in label_text)
            and re.search(r"(^|[^a-z])pt([^a-z]|$)|platinum", label_text)
        ):
            role_material_bonus += 60
        if (
            node.get("type") == "Cathode"
            and "cu" in joined_query
            and "carbon paper" in joined_query
            and re.search(r"(^|[^a-z])cu([^a-z]|$)|copper", label_text)
            and any(term in label_text for term in ("carbon paper", "carbon fiber paper", "gdl", "gas diffusion layer"))
        ):
            role_material_bonus += 35
        by_type[str(node.get("type") or "unknown")].append((role_material_bonus, hits, exact_label_hits, str(node.get("node_id") or ""), node["node_id"]))
    for node_type in by_type:
        by_type[node_type].sort(reverse=True)
    return by_type


def type_balanced_anchor_ids(nodes: list[dict], query_terms: list[str], max_anchors: int = EGO_ANCHORS) -> tuple[set[str], dict]:
    by_type = score_nodes_by_type(nodes, query_terms)
    selected: list[str] = []
    selected_set: set[str] = set()
    selected_by_type: dict[str, int] = defaultdict(int)
    role_types = [node_type for node_type in role_relevant_types(query_terms) if node_type in by_type]

    def add_from_type(node_type: str, quota: int) -> None:
        for item in by_type.get(node_type, []):
            node_id = item[-1]
            if len(selected) >= max_anchors or selected_by_type[node_type] >= quota:
                break
            if node_id in selected_set:
                continue
            selected.append(node_id)
            selected_set.add(node_id)
            selected_by_type[node_type] += 1

    role_progress = True
    while role_progress and len(selected) < max_anchors:
        role_progress = False
        for node_type in role_types:
            if selected_by_type[node_type] >= EGO_ROLE_TYPE_QUOTA:
                continue
            before = len(selected)
            add_from_type(node_type, selected_by_type[node_type] + 1)
            role_progress = role_progress or len(selected) > before
            if len(selected) >= max_anchors:
                break

    type_names = sorted(by_type, key=lambda node_type: (-len(by_type[node_type]), node_type))
    while len(selected) < max_anchors:
        progressed = False
        for node_type in type_names:
            target_quota = max(EGO_TYPE_QUOTA, selected_by_type[node_type] + 1)
            before = len(selected)
            add_from_type(node_type, target_quota)
            progressed = progressed or len(selected) > before
            if len(selected) >= max_anchors:
                break
        if not progressed:
            break

    return set(selected), {
        "anchor_selection": "type_balanced_role_disambiguated",
        "role_types": role_types,
        "anchors_by_type": dict(sorted(selected_by_type.items())),
        "candidate_nodes_by_type": {node_type: len(items) for node_type, items in sorted(by_type.items())},
    }


def selected_transport_counts(edges: list[dict], node_by_id: dict[str, dict], transport_dimensions: dict[str, tuple[str, ...]]) -> dict[str, dict[str, int]]:
    counts = {dimension: {"candidate_edges": 0, "global_candidate_edges": 0, "selected_edges": 0} for dimension in transport_dimensions}
    for edge in edges:
        text = edge_text(edge, node_by_id)
        for dimension, terms in transport_dimensions.items():
            if any(term.lower() in text for term in terms):
                counts[dimension]["candidate_edges"] += 1
                counts[dimension]["selected_edges"] += 1
    counts["_total"] = {"candidate_edges": len(edges), "selected_edges": len(edges)}
    return counts


def ego_graph_subgraph(
    nodes: list[dict],
    edges: list[dict],
    node_by_id: dict[str, dict],
    diagnosis: str,
    query_terms: list[str],
    anchor_terms: list[str] | None = None,
    transport_dimensions: dict[str, tuple[str, ...]] | None = None,
    max_edges: int = MAX_EDGES,
) -> tuple[dict, dict]:
    retrieval_terms = list(dict.fromkeys([*query_terms, *(anchor_terms or [])]))
    expanded_terms = anchor_query_terms(retrieval_terms)
    anchor_ids, anchor_meta = type_balanced_anchor_ids(nodes, expanded_terms)
    chain_candidates, chain_counts = chain_edges(anchor_ids, edges)
    chain_candidates = dedupe_edges(chain_candidates)
    query = tokens(" ".join([diagnosis, *expanded_terms]))
    vectors = [tokens(edge_text(edge, node_by_id)) for edge in chain_candidates]
    relevance = [cosine(query, vector) for vector in vectors]
    preferred_system = preferred_reaction_system(expanded_terms, diagnosis)
    reaction_priorities = [reaction_system_priority(edge, preferred_system) for edge in chain_candidates]
    one_hop_indices = [
        idx
        for idx, edge in enumerate(chain_candidates)
        if edge.get("src") in anchor_ids or edge.get("dst") in anchor_ids
    ]
    one_hop_ranked = sorted(one_hop_indices, key=lambda idx: (reaction_priorities[idx], relevance[idx]), reverse=True)
    selected_indices = one_hop_ranked[:max_edges]
    selected_keys = {edge_key(chain_candidates[idx]) for idx in selected_indices}
    if len(selected_indices) < max_edges:
        ranked = sorted(range(len(chain_candidates)), key=lambda idx: (reaction_priorities[idx], relevance[idx]), reverse=True)
        for idx in ranked:
            key = edge_key(chain_candidates[idx])
            if key in selected_keys:
                continue
            selected_indices.append(idx)
            selected_keys.add(key)
            if len(selected_indices) >= max_edges:
                break
    selected_edges = [strip_internal_edge_fields(chain_candidates[idx]) for idx in selected_indices]
    node_ids = {edge["src"] for edge in selected_edges} | {edge["dst"] for edge in selected_edges} | anchor_ids
    subgraph = {
        "nodes": [node_by_id[node_id] for node_id in sorted(node_ids) if node_id in node_by_id],
        "edges": selected_edges,
    }
    meta = {
        "algorithm": "C_egograph_v2",
        "query_boundary": "diagnosis_anchors_only",
        "anchor_count": len(anchor_ids),
        "anchor_ids": sorted(anchor_ids),
        "anchor_one_hop_edges": len(one_hop_indices),
        "candidate_edges": len(chain_candidates),
        "chain_counts": chain_counts,
        "selection": "type_balanced_anchors_then_preserve_one_hop_edges_then_fill_by_local_token_cosine",
        "preferred_reaction_system": preferred_system,
        "reaction_system_selection": "preferred_system_then_transferable_then_unknown_then_other_before_token_cosine",
        "candidate_reaction_system_counts": reaction_system_counts(chain_candidates),
        "selected_reaction_system_counts": reaction_system_counts(selected_edges),
        "query_terms": expanded_terms,
        "diagnosis_query_terms": query_terms,
        "retrieval_anchor_terms": anchor_terms or [],
        **anchor_meta,
    }
    if transport_dimensions is not None:
        meta["transport_dimension_counts"] = selected_transport_counts(selected_edges, node_by_id, transport_dimensions)
    return subgraph, meta
