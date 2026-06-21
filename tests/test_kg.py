from __future__ import annotations

import json

from reactor_agent.contracts import ExtractedKGEdge, ExtractedKGNode, KGPaperExtraction
from reactor_agent.steps import kg
from reactor_agent.steps.kg import _merge_extractions, build_kg, validate_kg
from reactor_agent.steps.kg_visualize import build_visualizations


def test_merge_discards_edge_signature_violations():
    extraction = KGPaperExtraction(
        doc_id="doc_0001",
        nodes=[
            ExtractedKGNode(node_id="paper:doc_0001", type="Paper", label="Paper 1", props=[]),
            ExtractedKGNode(node_id="koh", type="Electrolyte", label="1 M KOH", props=[]),
            ExtractedKGNode(node_id="voltage", type="Performance", label="cell voltage", props=[]),
            ExtractedKGNode(node_id="flood", type="Failure Mode", label="flooding", props=[]),
        ],
        edges=[
            ExtractedKGEdge(
                src="Electrolyte:KOH_electrolyte",
                dst="Performance:cell_voltage",
                relation="causes_risk",
                source_doc_id="doc_0001",
                source_chunk_id="chunk_1",
                experiment_ref=None,
            ),
            ExtractedKGEdge(
                src="Electrolyte:KOH_electrolyte",
                dst="Failure_Mode:flooding",
                relation="causes_risk",
                source_doc_id="doc_0001",
                source_chunk_id="chunk_2",
                experiment_ref=None,
            ),
        ],
    )

    nodes, edges, discarded = _merge_extractions(
        [extraction],
        {"doc_0001": {"title": "Paper 1", "doi": "10.1/example", "lib": "lib1", "class_name": "classA"}},
    )

    assert len(edges) == 1
    assert edges[0]["dst"] == "Failure_Mode:flooding"
    assert discarded[0]["reason"] == "edge_signature_violation"
    assert validate_kg(nodes, edges) == []


def test_build_visualizations_writes_index_and_overview(tmp_path):
    kg_dir = tmp_path / "kg"
    kg_dir.mkdir()
    (kg_dir / "kg_nodes.json").write_text(
        json.dumps(
            [
                {"node_id": "Reactor:Flow_cell", "type": "Reactor", "label": "Flow cell", "props": {}},
                {"node_id": "Cathode:GDE", "type": "Cathode", "label": "GDE", "props": {}},
                {"node_id": "Failure_Mode:flooding", "type": "Failure Mode", "label": "flooding", "props": {}},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (kg_dir / "kg_edges.json").write_text(
        json.dumps(
            [
                {
                    "src": "Reactor:Flow_cell",
                    "dst": "Cathode:GDE",
                    "relation": "has_component",
                    "source_doc_id": "doc_0001",
                    "source_chunk_id": "chunk_1",
                    "experiment_ref": None,
                },
                {
                    "src": "Cathode:GDE",
                    "dst": "Failure_Mode:flooding",
                    "relation": "causes_risk",
                    "source_doc_id": "doc_0001",
                    "source_chunk_id": "chunk_2",
                    "experiment_ref": None,
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = build_visualizations(kg_dir, cache_lib=False)

    assert result["graphs"] == 1
    assert (kg_dir / "viz" / "index.html").exists()
    assert (kg_dir / "viz" / "overview.html").exists()
    assert "知识图谱可视化索引" in (kg_dir / "viz" / "index.html").read_text(encoding="utf-8")


def test_build_kg_generates_visualization_in_pipeline(tmp_path, monkeypatch):
    step1_dir = tmp_path / "step1"
    step1_dir.mkdir()
    filtered_core = tmp_path / "filtered_core.json"
    out_dir = tmp_path / "kg_out"
    (step1_dir / "paper_facts.json").write_text(
        json.dumps([{"doc_id": "doc_0001", "doi": "10.1/example"}]),
        encoding="utf-8",
    )
    (step1_dir / "core_papers.json").write_text(
        json.dumps([{"doc_id": "doc_0001", "doi": "10.1/example", "title": "Paper 1"}]),
        encoding="utf-8",
    )
    filtered_core.write_text(json.dumps([{"doc_id": "doc_0001"}]), encoding="utf-8")

    def fake_extract_paper_kg(paper):
        return KGPaperExtraction(
            doc_id=paper["doc_id"],
            nodes=[
                ExtractedKGNode(node_id="paper:doc_0001", type="Paper", label="Paper 1", props=[]),
                ExtractedKGNode(node_id="flow_cell", type="Reactor", label="Flow cell", props=[]),
                ExtractedKGNode(node_id="gde", type="Cathode", label="GDE", props=[]),
                ExtractedKGNode(node_id="flood", type="Failure Mode", label="flooding", props=[]),
            ],
            edges=[
                ExtractedKGEdge(
                    src="Reactor:Flow_cell",
                    dst="Cathode:GDE",
                    relation="has_component",
                    source_doc_id="doc_0001",
                    source_chunk_id="chunk_1",
                    experiment_ref=None,
                ),
                ExtractedKGEdge(
                    src="Cathode:GDE",
                    dst="Failure_Mode:flooding",
                    relation="causes_risk",
                    source_doc_id="doc_0001",
                    source_chunk_id="chunk_2",
                    experiment_ref=None,
                ),
            ],
        )

    monkeypatch.setattr(kg, "_extract_paper_kg", fake_extract_paper_kg)

    summary = build_kg(step1_dir, filtered_core, out_dir, concurrency=1, viz_cache_lib=False)

    assert summary["visualization"]["index_html"].endswith("viz\\index.html") or summary["visualization"]["index_html"].endswith("viz/index.html")
    assert (out_dir / "viz" / "index.html").exists()
    assert (out_dir / "viz" / "overview.html").exists()
