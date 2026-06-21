from reactor_agent.steps import kg_reaction_system, reasoning_retrieval


def test_classify_reaction_system_labels_core_cases():
    assert kg_reaction_system.classify_reaction_system("CO2 reduction on Ag cathode")[0] == "CO2RR"
    assert kg_reaction_system.classify_reaction_system("CO reduction with CO feed on Cu")[0] == "CORR"
    assert kg_reaction_system.classify_reaction_system("PTFE porous diaphragm lowers ohmic loss")[0] == "transferable"
    assert kg_reaction_system.classify_reaction_system("unrelated synthesis detail")[0] == "unknown"


def test_ego_graph_prefers_reaction_system_edges_for_round_context():
    nodes = [
        {"node_id": "Diagnosis:co_reduction", "type": "Diagnosis", "label": "CO reduction diagnosis", "props": {}},
        {"node_id": "Cathode:cu", "type": "Cathode", "label": "Cu cathode", "props": {}},
        {"node_id": "Cathode:ag", "type": "Cathode", "label": "Ag CO2 cathode", "props": {}},
        {"node_id": "Performance:corr", "type": "Performance", "label": "CO reduction performance", "props": {}},
        {"node_id": "Performance:co2", "type": "Performance", "label": "CO2 reduction performance", "props": {}},
    ]
    edges = [
        {
            "src": "Diagnosis:co_reduction",
            "dst": "Cathode:ag",
            "relation": "supports",
            "source_doc_id": "doc_co2",
            "source_chunk_id": "chunk_co2",
            "experiment_ref": None,
            "reaction_system": "CO2RR",
        },
        {
            "src": "Diagnosis:co_reduction",
            "dst": "Performance:corr",
            "relation": "supports",
            "source_doc_id": "doc_corr",
            "source_chunk_id": "chunk_corr",
            "experiment_ref": None,
            "reaction_system": "CORR",
        },
        {
            "src": "Diagnosis:co_reduction",
            "dst": "Performance:co2",
            "relation": "supports",
            "source_doc_id": "doc_co2_b",
            "source_chunk_id": "chunk_co2_b",
            "experiment_ref": None,
            "reaction_system": "CO2RR",
        },
    ]
    node_by_id = {node["node_id"]: node for node in nodes}
    subgraph, meta = reasoning_retrieval.ego_graph_subgraph(
        nodes,
        edges,
        node_by_id,
        diagnosis="CO reduction / CORR direction",
        query_terms=["CO reduction", "CORR"],
        max_edges=1,
    )
    assert meta["preferred_reaction_system"] == "CORR"
    assert meta["selected_reaction_system_counts"]["CORR"] == 1
    assert subgraph["edges"][0]["source_doc_id"] == "doc_corr"
