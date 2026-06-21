from __future__ import annotations

import json
from pathlib import Path

from reactor_agent.steps import retrieval_ablation


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_run_ablation_writes_three_algorithm_outputs(tmp_path: Path):
    kg_dir = tmp_path / "kg"
    nodes = [
        {"node_id": "Failure_Mode:flooding", "type": "Failure Mode", "label": "flooding", "props": {}},
        {"node_id": "Reactor:gde", "type": "Reactor", "label": "gas diffusion electrode", "props": {}},
        {"node_id": "Performance:transport", "type": "Performance", "label": "better mass transport", "props": {}},
        {"node_id": "Paper:doc_1", "type": "Paper", "label": "Paper 1", "props": {"doc_id": "doc_1"}},
    ]
    edges = [
        {"src": "Failure_Mode:flooding", "dst": "Reactor:gde", "relation": "caused_by", "source_doc_id": "doc_1", "source_chunk_id": "c1"},
        {"src": "Reactor:gde", "dst": "Performance:transport", "relation": "improves", "source_doc_id": "doc_1", "source_chunk_id": "c2"},
    ]
    _write_json(kg_dir / "kg_nodes.json", nodes)
    _write_json(kg_dir / "kg_edges.json", edges)

    out_dir = tmp_path / "ablation"
    rows = retrieval_ablation.run_ablation(kg_dir, out_dir)

    assert len(rows) == 21
    assert (out_dir / "COMPARISON.md").exists()
    for algorithm in retrieval_ablation.ALGORITHMS:
        assert (out_dir / algorithm / "R1" / "subgraph.json").exists()
        assert (out_dir / algorithm / "R1" / "metrics.json").exists()


def test_eval_keywords_are_not_algorithm_metadata(tmp_path: Path):
    kg_dir = tmp_path / "kg"
    nodes = [
        {"node_id": "Diagnosis:pressure", "type": "Diagnosis", "label": "pressure", "props": {}},
        {"node_id": "Performance:stable", "type": "Performance", "label": "stable operation", "props": {}},
    ]
    edges = [
        {"src": "Diagnosis:pressure", "dst": "Performance:stable", "relation": "supports", "source_doc_id": "doc_1", "source_chunk_id": "c1"}
    ]
    _write_json(kg_dir / "kg_nodes.json", nodes)
    _write_json(kg_dir / "kg_edges.json", edges)

    rows = retrieval_ablation.run_ablation(kg_dir, tmp_path / "out")
    metadata_blob = json.dumps([row["metadata"] for row in rows], ensure_ascii=False).lower()

    assert "porous ptfe" not in metadata_blob
    assert "pt@ptl" not in metadata_blob


def test_c2_anchor_selection_keeps_separator_ptfe_role():
    nodes = [
        {"node_id": f"Cathode:PTFE_catalyst_{idx}", "type": "Cathode", "label": f"PTFE catalyst layer {idx}", "props": {}}
        for idx in range(12)
    ]
    nodes.append({"node_id": "Separator:PTFE_porous_diaphragm", "type": "Separator", "label": "PTFE porous diaphragm", "props": {}})

    anchor_ids, meta = retrieval_ablation._type_balanced_anchor_ids(nodes, ["PTFE", "separator", "membrane"], max_anchors=6)

    assert "Separator:PTFE_porous_diaphragm" in anchor_ids
    assert meta["anchors_by_type"]["Separator"] >= 1
