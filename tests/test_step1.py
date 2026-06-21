from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from reactor_agent import llm
from reactor_agent.contracts import Fact, PaperFacts
from reactor_agent.retrieval import search
from reactor_agent.steps.literature import build_literature_db, build_step1_output, extract_paper_facts, select_core_papers
from reactor_agent.steps.literature import (
    build_literature_db_from_chunks,
    load_chunk_records,
    load_chunks,
    run_step1_chunk_file_extraction,
    run_step1_extraction,
    select_by_group,
)


CORE_ROOT = Path(r"C:\Users\logan\Desktop\project2_strict_workspace_archive_20260617\core")
FULL_ROOT = Path(r"C:\Users\logan\Desktop\project2_strict")


def _write_sample_library(root: Path, n_docs: int = 2) -> Path:
    library = root / "library"
    parsed = library / "parsed"
    manifest_dir = library / "manifests"
    parsed.mkdir(parents=True)
    manifest_dir.mkdir(parents=True)

    rows = ["doc_id,doi,title"]
    for idx in range(1, n_docs + 1):
        doc_id = f"doc_{idx:04d}"
        rows.append(f"{doc_id},10.1/{idx},Paper {idx}")
        payload = {
            "blocks": [
                {
                    "page_num": 1,
                    "text": (
                        "This reactor uses a porous membrane separator. "
                        "The feed is 1 M KOH. "
                        "The system shows performance and stability data. "
                        "Flooding failure is discussed after operation."
                    ),
                }
            ]
        }
        (parsed / f"{doc_id}.json").write_text(json.dumps(payload), encoding="utf-8")
    (manifest_dir / "source_json_deduped_sample.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return library


def _llm_extraction(doc_id: str = "doc_0001", doi: str = "10.1/1", chunk_id: str = "0001_01") -> PaperFacts:
    return PaperFacts(
        doc_id=doc_id,
        doi=doi,
        structure=[Fact(value="structure fact", chunk_id=chunk_id, section_title="Results")],
        reaction=[Fact(value="reaction fact", chunk_id=chunk_id, section_title="Results")],
        membrane=[Fact(value="membrane fact", chunk_id=chunk_id, section_title="Results")],
        feed=[Fact(value="feed fact", chunk_id=chunk_id, section_title="Results")],
        performance=[Fact(value="performance fact", chunk_id=chunk_id, section_title="Results")],
        failure=[Fact(value="failure fact", chunk_id=chunk_id, section_title="Results")],
    )


def test_build_literature_db(tmp_path: Path):
    library = _write_sample_library(tmp_path)
    out_dir = tmp_path / "out"
    stats = build_literature_db(str(library), str(out_dir))
    assert stats["n_docs"] == 2
    assert stats["n_chunks"] == 2
    db_path = out_dir / "literature.db"
    assert db_path.exists()
    con = sqlite3.connect(db_path)
    assert con.execute("SELECT COUNT(*) FROM paper_summary").fetchone()[0] == 2


def test_select_core_requires_enough_papers(tmp_path: Path):
    library = _write_sample_library(tmp_path, n_docs=2)
    out_dir = tmp_path / "out"
    build_literature_db(str(library), str(out_dir))
    with pytest.raises(ValueError, match="not enough papers"):
        select_core_papers(str(out_dir / "literature.db"), anchors=[], min_count=30)


def test_extract_paper_facts_requires_llm_when_not_configured():
    chunks = [{"chunk_id": "0001_01", "text": "This reactor uses a porous membrane separator.", "doi": "10.1/1"}]
    with pytest.raises(llm.LLMStructuredError):
        extract_paper_facts("doc_0001", chunks)


def test_extract_paper_facts_uses_structured_llm(monkeypatch: pytest.MonkeyPatch):
    calls = []

    def fake_call(role, system, user, schema, images=None):
        calls.append({"role": role, "system": system, "user": user, "schema": schema})
        payload = json.loads(user)
        return _llm_extraction(payload["doc_id"], payload["doi"], payload["chunks"][0]["chunk_id"])

    monkeypatch.setattr(llm, "call", fake_call)
    chunks = [{"chunk_id": "0001_01", "text": "This reactor uses a porous membrane separator.", "doi": "10.1/1"}]
    facts = extract_paper_facts("doc_0001", chunks)
    assert len(facts.model_dump()) == 8
    assert facts.structure[0].chunk_id == "0001_01"
    assert calls[0]["role"] == "literature"
    assert calls[0]["schema"] is PaperFacts


def test_build_step1_output_requires_llm(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    def fake_call(role, system, user, schema, images=None):
        payload = json.loads(user)
        return _llm_extraction(payload["doc_id"], payload["doi"], payload["chunks"][0]["chunk_id"])

    monkeypatch.setattr(llm, "call", fake_call)
    library = _write_sample_library(tmp_path)
    out_dir = tmp_path / "out"
    output = build_step1_output(str(library), str(out_dir), min_core_count=1)
    assert output["db"]["n_docs"] == 2
    assert (out_dir / "step1_output.json").exists()
    assert (out_dir / "core_papers.json").exists()
    assert (out_dir / "facts.json").exists()


def test_search(tmp_path: Path):
    library = _write_sample_library(tmp_path)
    out_dir = tmp_path / "out"
    build_literature_db(str(library), str(out_dir))
    results = search("membrane KOH", top_k=2, db_path=out_dir / "literature.db")
    assert results
    assert results[0].doc_id == "doc_0001"


def test_load_real_chunk_schema_csv(tmp_path: Path):
    chunk_file = tmp_path / "chunks.csv"
    chunk_file.write_text(
        "\n".join(
            [
                "doc_id,filename,page_number,paragraph_id,chunk_id,char_start,char_end,text,clean_text,section_title,chunk_type,source_block_type,source_block_id",
                'doc_0001,10.1001_archpsyc.1973.01750320098015.json,1,doc_0001_p001_0001,doc_0001_chunk_000001,0,36,A Comparison in Agoraphobic Patients,A Comparison in Agoraphobic Patients,Brief and Prolonged Flooding,body_paragraph,paragraph,2',
                'doc_0001,10.1001_archpsyc.1973.01750320098015.json,1,doc_0001_p001_0002,doc_0001_chunk_000002,38,99,"Richard Stern, MD, DPM, and Isaac Marks, MD, MRCPsych, London","Richard Stern, MD, DPM, and Isaac Marks, MD, MRCPsych, London",Brief and Prolonged Flooding,body_paragraph,paragraph,3',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    records = load_chunk_records(chunk_file)
    assert len(records) == 2
    assert records[0].doc_id == "doc_0001"
    assert records[0].chunk_id == "doc_0001_chunk_000001"


def test_build_literature_db_from_chunks(tmp_path: Path):
    chunk_file = tmp_path / "chunks.csv"
    chunk_file.write_text(
        "\n".join(
            [
                "doc_id,filename,page_number,paragraph_id,chunk_id,char_start,char_end,text,clean_text,section_title,chunk_type,source_block_type,source_block_id",
                'doc_0001,10.1001_archpsyc.1973.01750320098015.json,1,doc_0001_p001_0001,doc_0001_chunk_000001,0,36,A Comparison in Agoraphobic Patients,A Comparison in Agoraphobic Patients,Brief and Prolonged Flooding,body_paragraph,paragraph,2',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    stats = build_literature_db_from_chunks(str(chunk_file), str(out_dir))
    assert stats["n_docs"] == 1
    assert stats["n_chunks"] == 1
    assert (out_dir / "literature.db").exists()


def test_run_step1_chunk_file_extraction_join_only(tmp_path: Path):
    chunk_file = tmp_path / "chunks.csv"
    chunk_file.write_text(
        "\n".join(
            [
                "doc_id,filename,page_number,paragraph_id,chunk_id,char_start,char_end,text,clean_text,section_title,chunk_type,source_block_type,source_block_id",
                'doc_0001,lib1__classA__10.1002_adma.201504766.json,1,doc_0001_p001_0001,doc_0001_chunk_000001,0,36,Reactor membrane text,Reactor membrane text,Intro,body_paragraph,text,2',
                'doc_0001,lib1__classA__10.1002_adma.201504766.json,1,doc_0001_p001_0002,doc_0001_chunk_000002,38,99,KOH feed text,KOH feed text,Results,body_paragraph,text,3',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    output = run_step1_chunk_file_extraction(chunk_file, out_dir, join_only=True)
    assert output["join_only"] is True
    assert output["core_papers"][0]["doi"] == "10.1002/adma.201504766"
    assert output["core_papers"][0]["lib"] == "lib1"
    assert output["core_papers"][0]["class_name"] == "classA"
    assert (out_dir / "chunk_join_manifest.json").exists()
    assert (out_dir / "core_papers.json").exists()


def test_select_by_group_real_manifest():
    if not FULL_ROOT.exists():
        pytest.skip(f"full library root not found: {FULL_ROOT}")
    dois = select_by_group("lib4", ["classA", "classB"], library_root=FULL_ROOT)
    assert dois
    assert all(doi.startswith("10.") for doi in dois)


def test_load_core_anchor_chunks_real_paths():
    if not CORE_ROOT.exists():
        pytest.skip(f"core library root not found: {CORE_ROOT}")
    anchor_dois = [
        "10.1038/s41586-023-06792-0",
        "10.1038/s41560-020-00761-x",
        "10.1038/s41560-019-0451-x",
        "10.1038/s41467-020-17403-1",
        "10.1038/s41467-023-43300-4",
        "10.1038/s41586-023-05918-8",
        "10.1002/cssc.201902547",
        "10.1021/acs.chemrev.3c00206",
    ]
    chunks = load_chunks(anchor_dois, library_root=CORE_ROOT)
    assert {chunk["doi"] for chunk in chunks} == set(anchor_dois)
    assert len({chunk["doc_id"] for chunk in chunks}) == 8
    assert all(chunk["chunk_id"] and chunk["clean_text"] for chunk in chunks)


def test_run_step1_join_only_real_paths(tmp_path: Path):
    if not CORE_ROOT.exists():
        pytest.skip(f"core library root not found: {CORE_ROOT}")
    output = run_step1_extraction(["10.1038/s41586-023-06792-0"], CORE_ROOT, tmp_path / "out", join_only=True)
    assert output["join_only"] is True
    assert len(output["core_papers"]) == 1
    assert (tmp_path / "out" / "chunk_join_manifest.json").exists()
    assert (tmp_path / "out" / "core_papers.json").exists()
    assert not (tmp_path / "out" / "paper_facts.json").exists()
