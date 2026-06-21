from __future__ import annotations

import json
from pathlib import Path

from reactor_agent.steps import kg_normalize


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_normalize_ptfe_separator_rewrites_edges_and_keeps_cathode_separate(tmp_path: Path):
    kg_dir = tmp_path / "kg"
    out_dir = tmp_path / "normalized"
    synonym_map = tmp_path / "synonym_map.json"
    nodes = [
        {"node_id": "Separator:PTFE_porous_diaphragm", "type": "Separator", "label": "PTFE porous diaphragm", "props": {}},
        {"node_id": "Separator:PTFE_membrane", "type": "Separator", "label": "PTFE membrane", "props": {"material": "PTFE"}},
        {"node_id": "Separator:ePTFE_membrane", "type": "Separator", "label": "ePTFE membrane", "props": {"pore_size": "450 nm"}},
        {"node_id": "Cathode:PTFE_catalyst_layer", "type": "Cathode", "label": "PTFE catalyst layer", "props": {}},
        {"node_id": "Performance:stable_operation", "type": "Performance", "label": "stable operation", "props": {}},
        {"node_id": "Failure_Mode:flooding", "type": "Failure Mode", "label": "flooding", "props": {}},
    ]
    edges = [
        {
            "src": "Separator:PTFE_membrane",
            "dst": "Performance:stable_operation",
            "relation": "improves",
            "source_doc_id": "doc_1",
            "source_chunk_id": "c1",
            "experiment_ref": None,
        },
        {
            "src": "Separator:ePTFE_membrane",
            "dst": "Performance:stable_operation",
            "relation": "improves",
            "source_doc_id": "doc_1",
            "source_chunk_id": "c1",
            "experiment_ref": None,
        },
        {
            "src": "Cathode:PTFE_catalyst_layer",
            "dst": "Failure_Mode:flooding",
            "relation": "causes_risk",
            "source_doc_id": "doc_2",
            "source_chunk_id": "c2",
            "experiment_ref": None,
        },
    ]
    _write_json(kg_dir / "kg_nodes.json", nodes)
    _write_json(kg_dir / "kg_edges.json", edges)
    _write_json(
        synonym_map,
        {
            "groups": [
                {
                    "name": "ptfe_separator_diaphragm",
                    "type": "Separator",
                    "canonical_node_id": "Separator:porous_PTFE_diaphragm",
                    "canonical_label": "porous PTFE diaphragm",
                    "aliases": ["Separator:PTFE_porous_diaphragm", "Separator:PTFE_membrane", "Separator:ePTFE_membrane"],
                }
            ]
        },
    )

    summary = kg_normalize.normalize_kg(kg_dir, out_dir, synonym_map, visualize=False)
    out_nodes = json.loads((out_dir / "kg_nodes.json").read_text(encoding="utf-8"))
    out_edges = json.loads((out_dir / "kg_edges.json").read_text(encoding="utf-8"))
    out_node_ids = {node["node_id"] for node in out_nodes}

    assert summary["nodes"] == 4
    assert summary["edges"] == 2
    assert "Separator:porous_PTFE_diaphragm" in out_node_ids
    assert "Separator:PTFE_membrane" not in out_node_ids
    assert "Cathode:PTFE_catalyst_layer" in out_node_ids
    assert sum(1 for edge in out_edges if edge["src"] == "Separator:porous_PTFE_diaphragm") == 1
    assert any(edge["src"] == "Cathode:PTFE_catalyst_layer" for edge in out_edges)
    canonical = next(node for node in out_nodes if node["node_id"] == "Separator:porous_PTFE_diaphragm")
    assert canonical["props"]["synonym_members"] == [
        "Separator:PTFE_membrane",
        "Separator:PTFE_porous_diaphragm",
        "Separator:ePTFE_membrane",
    ]
    assert summary["traceable_edges"] == summary["edges"]
