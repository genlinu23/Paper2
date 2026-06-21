from __future__ import annotations

import json
from pathlib import Path

import pytest

from reactor_agent import llm
from reactor_agent.contracts import BuildSheet, ReactorRecommendation
from reactor_agent.steps import reasoning


def test_check_redlines():
    assert reasoning.check_redlines("gas-aerosol-solid contacting") == []
    assert reasoning.check_redlines("气固两相流") == ["forbidden term: 气固两相流"]
    assert reasoning.check_redlines("AEM provides K+") == ["forbidden term: AEM provides K+"]
    assert reasoning.check_redlines("PTFE gas-access backing pressed near an anion-exchange membrane") == []
    assert reasoning.check_redlines("PTFE is used as an ion-exchange membrane") == ["forbidden term: PTFE as ion exchange membrane"]


def test_fetch_reasoning_context_uses_kg():
    ctx = reasoning.fetch_reasoning_context(
        Path(r"C:\Users\logan\reactor_agent\outputs\step2_causal_kg_d2_v2"),
        "R2",
        "flooding",
    )
    assert "subgraph" in ctx and "refs" in ctx and "prev_failures" in ctx
    assert "transport_dimension_counts" in ctx
    assert ctx["subgraph"]["nodes"]
    assert isinstance(ctx["refs"], list)


def test_run_reasoning_with_fake_llm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    calls = []

    def fake_call(role, system, user, schema, images=None):
        calls.append((role, schema.__name__))
        payload = json.loads(user)
        if schema is ReactorRecommendation:
            refs = payload["literature_refs"][:3]
            return ReactorRecommendation(
                round_id=payload["round_id"],
                prev_failure_mode=payload["prev_failure_mode"],
                primary_bottleneck="pressure",
                hypothesis="Use double-sided gas operation with AEM to avoid the thick liquid interlayer.",
                new_architecture="CORR / AEM / HOR double-sided gas reactor",
                design_change=["replace thick liquid interlayer with CORR / AEM / HOR double-sided gas operation"],
                rationale="KG evidence supports removing the flooding-prone liquid layer.",
                expected_improvement="lower flooding and lower pressure drop",
                key_risks=["dry-out", "crossover"],
                min_experiment=["CP", "EIS", "photo"],
                discriminating_test=["compare against previous architecture"],
                diagnostic_trigger=["flooding remains dominant"],
                go_no_go="continue",
                literature_refs=refs,
                score=82.5,
            )
        raise AssertionError(f"unexpected schema {schema}")

    monkeypatch.setattr(llm, "call", fake_call)
    out = reasoning.run_reasoning(
        "R2",
        tmp_path,
        "flooding",
        kg_dir=Path(r"C:\Users\logan\reactor_agent\outputs\step2_causal_kg_d2_v2"),
    )
    assert out.round_id == "R2"
    out_dir = tmp_path / "outputs" / "step3_reasoning_replay_v1" / "rounds" / "R2"
    assert (out_dir / "D3_memo.json").exists()
    assert (out_dir / "D3_memo.md").exists()
    assert (out_dir / "D3_build_sheet.json").exists()
    assert (out_dir / "D3_build_sheet.md").exists()
    assert (out_dir / "run_config.json").exists()
    assert calls and calls[0][0] == "reasoning"


def test_run_replay_uses_all_rounds(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    seen = []
    diagnoses = []

    def fake_run_reasoning(round_id, project_root, last_diagnosis, kg_dir=None, output_dir=None):
        seen.append(round_id)
        diagnoses.append(last_diagnosis)
        return ReactorRecommendation(
            round_id=round_id,
            prev_failure_mode=["x"],
            primary_bottleneck="pressure",
            hypothesis="h",
            new_architecture="n",
            design_change=["d"],
            rationale="r",
            expected_improvement="e",
            key_risks=["k"],
            min_experiment=["m"],
            discriminating_test=["t"],
            diagnostic_trigger=["g"],
            go_no_go="continue",
            literature_refs=[
                {"doc_id": "doc_1", "doi": "10.1/a", "title": "A"},
                {"doc_id": "doc_2", "doi": "10.1/b", "title": "B"},
                {"doc_id": "doc_3", "doi": "10.1/c", "title": "C"},
            ],
            score=1.0,
        )

    monkeypatch.setattr(reasoning, "run_reasoning", fake_run_reasoning)
    result = reasoning.run_replay(tmp_path, kg_dir=Path(r"C:\Users\logan\reactor_agent\outputs\step2_causal_kg_d2_v2"))
    assert seen == reasoning.ROUND_ORDER
    assert len(result) == 7
    assert (tmp_path / "outputs" / "step3_reasoning_replay_v1" / "replay_summary.json").exists()
    assert diagnoses == [reasoning.ROUND_DIAGNOSES[round_id] for round_id in reasoning.ROUND_ORDER]


def test_run_replay_can_use_full_diagnoses(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    diagnoses = []

    def fake_run_reasoning(round_id, project_root, last_diagnosis, kg_dir=None, output_dir=None):
        diagnoses.append(last_diagnosis)
        return ReactorRecommendation(
            round_id=round_id,
            prev_failure_mode=[last_diagnosis],
            primary_bottleneck="pressure",
            hypothesis="h",
            new_architecture="n",
            design_change=["d"],
            rationale="r",
            expected_improvement="e",
            key_risks=["k"],
            min_experiment=["m"],
            discriminating_test=["t"],
            diagnostic_trigger=["g"],
            go_no_go="continue",
            literature_refs=[
                {"doc_id": "doc_1", "doi": "10.1/a", "title": "A"},
                {"doc_id": "doc_2", "doi": "10.1/b", "title": "B"},
                {"doc_id": "doc_3", "doi": "10.1/c", "title": "C"},
            ],
            score=1.0,
        )

    monkeypatch.setattr(reasoning, "run_reasoning", fake_run_reasoning)
    reasoning.run_replay(
        tmp_path,
        kg_dir=Path(r"C:\Users\logan\reactor_agent\outputs\step2_causal_kg_d2_v2"),
        diagnosis_mode="full",
    )
    assert diagnoses == [reasoning.FULL_ROUND_DIAGNOSES[round_id] for round_id in reasoning.ROUND_ORDER]


def test_full_diagnoses_do_not_contain_structure_answer():
    for round_id, diagnosis in reasoning.FULL_ROUND_DIAGNOSES.items():
        ok, patterns = reasoning._diagnosis_no_structure_answer(diagnosis)
        assert ok, (round_id, patterns)


def test_fetch_reasoning_context_has_transport_dimensions():
    ctx = reasoning.fetch_reasoning_context(
        Path(r"C:\Users\logan\reactor_agent\outputs\step2_causal_kg_d2_v2"),
        "R5",
        "carbon paper poor droplet transport",
    )
    counts = ctx["transport_dimension_counts"]
    assert isinstance(counts, dict)
    assert set(reasoning.TRANSPORT_DIMENSIONS).issubset(counts)
    assert any(item["candidate_edges"] >= 0 for item in counts.values() if isinstance(item, dict))


def test_r7_reasoning_target_does_not_require_ptl_anode():
    text = (
        "Aerosol spray supplies H2O and K+ for local cation availability. "
        "PTFE is used as a porous diaphragm for physical isolation and lower membrane cost."
    )
    match, notes = reasoning._compare_round_reasoning_target("R7", text)
    structure_match, structure_notes = reasoning._compare_taskbook_structure("R7", text)
    assert match, notes
    assert not structure_match
    assert any("ptl" in group for group in structure_notes["missing_groups"])
