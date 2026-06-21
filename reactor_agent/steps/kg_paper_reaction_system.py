from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .kg_reaction_system import TRANSFERABLE_PATTERNS, _write_csv, _write_json


PaperReactionSystem = Literal["CO2RR", "CORR", "both", "other_reaction", "non_reaction", "unknown"]
EdgeReactionSystem = Literal["CO2RR", "CORR", "transferable", "other_reaction", "unknown"]

DEFAULT_STEP1_DIR = Path(r"C:\Users\logan\reactor_agent\outputs\step1_run_ready_v2_chunks_v3")
DEFAULT_CHUNKS_CSV = Path(
    r"C:\Users\logan\Desktop\project2_strict\strict_clean_v2\final_rule_based_ab_v1\membership_aligned_dataset_v1\chunk_run_v3\03_text_chunks\body_chunks.csv"
)
DEFAULT_BASE_KG_DIR = Path(r"C:\Users\logan\reactor_agent\outputs\step2_causal_kg_v6_anode_edges")
DEFAULT_OUT_DIR = Path(r"C:\Users\logan\reactor_agent\outputs\step2_causal_kg_v8_paper_reaction_system")


class PaperReactionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reaction_system: PaperReactionSystem
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    evidence_terms: list[str]


SYSTEM_PROMPT = """Classify the paper-level reaction system from title, abstract, and conclusion only.

Allowed labels:
- CO2RR: carbon dioxide electroreduction / CO2 electrolysis is the paper's main reaction.
- CORR: carbon monoxide electroreduction / CO electrolysis / CO feed conversion is the paper's main reaction.
- both: both CO2RR and CORR are central paper-level reaction systems.
- other_reaction: an electrochemical reaction other than CO2RR/CORR is central, such as HER, HOR, ORR, OER, water electrolysis, fuel cells, batteries, or oxygen reduction.
- non_reaction: paper is mainly materials, membrane, transport, methods, or theory with no specific electrochemical reaction system.
- unknown: the provided title/abstract/conclusion is insufficient or ambiguous.

Rules:
- Judge the paper as a whole, not a single edge.
- Do not infer CORR from cobalt chemical symbol Co.
- Use unknown for low confidence.
- Return only the JSON schema.
"""


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _endpoint_from_base_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def _call_vectorengine(model: str, payload: dict, timeout_s: int = 120) -> dict:
    api_key = os.environ.get("VECTORENGINE_API_KEY")
    if not api_key:
        raise RuntimeError("VECTORENGINE_API_KEY is required.")
    base_url = os.environ.get("VECTORENGINE_BASE_URL", "https://api.vectorengine.cn/v1")
    body = {
        "model": model,
        "temperature": 0.0,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "PaperReactionDecision",
                "schema": PaperReactionDecision.model_json_schema(),
                "strict": True,
            },
        },
    }
    req = urllib.request.Request(
        _endpoint_from_base_url(base_url),
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as response:
        raw = json.loads(response.read().decode("utf-8"))
    content = raw["choices"][0]["message"]["content"]
    return json.loads(content)


def _section_kind(section_title: str, text: str, page_number: str) -> str | None:
    section = (section_title or "").strip().lower()
    clean = (text or "").strip().lower()
    if "abstract" in section:
        return "abstract"
    if any(term in section for term in ("conclusion", "conclusions", "summary", "outlook", "perspective")):
        return "conclusion"
    if page_number == "1" and len(clean) > 300 and not section:
        return "front_matter"
    return None


def _clip_join(items: list[str], limit: int) -> str:
    text = "\n".join(item.strip() for item in items if item and item.strip())
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def load_paper_inputs(step1_dir: str | Path, chunks_csv: str | Path, doc_ids: set[str]) -> dict[str, dict]:
    step1_path = Path(step1_dir)
    core_rows = _read_json(step1_path / "core_papers.json")
    if not isinstance(core_rows, list):
        raise ValueError("core_papers.json must be a JSON list")
    inputs = {
        row["doc_id"]: {
            "doc_id": row["doc_id"],
            "doi": row.get("doi"),
            "title": row.get("title") or "",
            "abstract_parts": [],
            "conclusion_parts": [],
            "front_matter_parts": [],
        }
        for row in core_rows
        if row.get("doc_id") in doc_ids
    }
    missing = sorted(doc_ids - set(inputs))
    if missing:
        raise ValueError(f"{len(missing)} KG doc_ids missing from core_papers.json; first={missing[:10]}")

    with Path(chunks_csv).open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            doc_id = row.get("doc_id")
            if doc_id not in inputs:
                continue
            text = row.get("clean_text") or row.get("text") or ""
            kind = _section_kind(row.get("section_title") or "", text, row.get("page_number") or "")
            if kind == "abstract":
                inputs[doc_id]["abstract_parts"].append(text)
            elif kind == "conclusion":
                inputs[doc_id]["conclusion_parts"].append(text)
            elif kind == "front_matter":
                inputs[doc_id]["front_matter_parts"].append(text)

    prepared = {}
    for doc_id, item in inputs.items():
        abstract = _clip_join(item["abstract_parts"], 2500)
        if not abstract:
            abstract = _clip_join(item["front_matter_parts"][:3], 1800)
        prepared[doc_id] = {
            "doc_id": doc_id,
            "doi": item["doi"],
            "title": item["title"],
            "abstract": abstract,
            "conclusion": _clip_join(item["conclusion_parts"], 3000),
        }
    return prepared


def _edge_doc_ids(edges: list[dict]) -> set[str]:
    return {_paper_doc_id(edge.get("source_doc_id")) for edge in edges if _paper_doc_id(edge.get("source_doc_id"))}


def _paper_doc_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.match(r"^(doc_\d+)", value.strip())
    return match.group(1) if match else value.strip() or None


def classify_one(doc: dict, model: str, min_confidence: float, max_retries: int = 3) -> dict:
    payload = {
        "doc_id": doc["doc_id"],
        "title": doc.get("title") or "",
        "abstract": doc.get("abstract") or "",
        "conclusion": doc.get("conclusion") or "",
    }
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            raw = _call_vectorengine(model, payload)
            decision = PaperReactionDecision.model_validate(raw)
            label = decision.reaction_system
            if decision.confidence < min_confidence:
                label = "unknown"
            return {
                **payload,
                "reaction_system": label,
                "raw_reaction_system": decision.reaction_system,
                "confidence": decision.confidence,
                "rationale": decision.rationale,
                "evidence_terms": decision.evidence_terms,
                "status": "ok",
                "attempt": attempt,
            }
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, KeyError, RuntimeError) as exc:
            last_error = str(exc)
            time.sleep(min(2 * attempt, 10))
    return {
        **payload,
        "reaction_system": "unknown",
        "raw_reaction_system": "unknown",
        "confidence": 0.0,
        "rationale": f"classification_failed: {last_error}",
        "evidence_terms": [],
        "status": "failed",
        "attempt": max_retries,
    }


def classify_papers(
    paper_inputs: dict[str, dict],
    out_dir: Path,
    model: str,
    min_confidence: float,
    concurrency: int,
    limit: int | None = None,
) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    per_doc_dir = out_dir / "paper_reaction_by_doc"
    per_doc_dir.mkdir(parents=True, exist_ok=True)
    doc_ids = sorted(paper_inputs)
    if limit is not None:
        doc_ids = doc_ids[:limit]
    results: list[dict] = []
    pending: list[str] = []
    for doc_id in doc_ids:
        cached = per_doc_dir / f"{doc_id}.json"
        if cached.exists():
            results.append(_read_json(cached))
        else:
            pending.append(doc_id)

    def task(doc_id: str) -> dict:
        result = classify_one(paper_inputs[doc_id], model=model, min_confidence=min_confidence)
        _write_json(per_doc_dir / f"{doc_id}.json", result)
        return result

    completed = 0
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(task, doc_id): doc_id for doc_id in pending}
        for future in as_completed(futures):
            results.append(future.result())
            completed += 1
            if completed == len(pending) or completed % 25 == 0:
                _write_json(
                    out_dir / "paper_reaction_progress.json",
                    {"completed_new": completed, "pending_at_start": len(pending), "total_results": len(results)},
                )
    return sorted(results, key=lambda row: row["doc_id"])


TRANSFERABLE_EDGE_RE = re.compile("|".join(f"(?:{pattern})" for pattern in TRANSFERABLE_PATTERNS))
REACTION_TEXT_RE = re.compile(
    r"\bco2rr\b|\bco2\b|\bco₂\b|\bcarbon dioxide\b|\bcorr\b|\bco reduction\b|\bcarbon monoxide\b|\bco feed\b|\bco gas\b|\bher\b|\bhor\b|\borr\b|\boer\b|\bhydrogen evolution\b|\bhydrogen oxidation\b|\boxygen reduction\b|\boxygen evolution\b|water electrolysis"
)


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
        ]
    ).lower()


def edge_label_from_paper(edge: dict, node_by_id: dict[str, dict], paper_label: str) -> str:
    text = _edge_text(edge, node_by_id)
    if paper_label in {"CO2RR", "CORR"}:
        return paper_label
    if paper_label == "both":
        return "transferable"
    if paper_label == "other_reaction":
        return "other_reaction"
    if paper_label == "non_reaction":
        if TRANSFERABLE_EDGE_RE.search(text) and not REACTION_TEXT_RE.search(text):
            return "transferable"
        return "unknown"
    return "unknown"


def write_annotated_kg(base_kg_dir: str | Path, out_dir: str | Path, paper_rows: list[dict], overwrite_kg: bool = True) -> dict:
    base_path = Path(base_kg_dir)
    out_path = Path(out_dir)
    if out_path.exists() and overwrite_kg:
        # Preserve per-doc classifications if this is also the classification output dir.
        for child in out_path.iterdir():
            if child.name == "paper_reaction_by_doc":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    out_path.mkdir(parents=True, exist_ok=True)
    nodes = _read_json(base_path / "kg_nodes.json")
    edges = _read_json(base_path / "kg_edges.json")
    node_by_id = {node["node_id"]: node for node in nodes}
    paper_by_doc = {row["doc_id"]: row for row in paper_rows}
    annotated_edges: list[dict] = []
    inherited = Counter()
    for edge in edges:
        paper_doc_id = _paper_doc_id(edge.get("source_doc_id"))
        paper_label = paper_by_doc.get(paper_doc_id, {}).get("reaction_system", "unknown")
        label = edge_label_from_paper(edge, node_by_id, paper_label)
        new_edge = dict(edge)
        new_edge["reaction_system"] = label
        new_edge["paper_reaction_system"] = paper_label
        new_edge["paper_doc_id"] = paper_doc_id
        annotated_edges.append(new_edge)
        inherited[(paper_label, label)] += 1

    for src in base_path.iterdir():
        if src.name in {"kg_nodes.json", "kg_edges.json", "kg_edges.csv"}:
            continue
        dst = out_path / src.name
        if dst.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    _write_json(out_path / "kg_nodes.json", nodes)
    _write_json(out_path / "kg_edges.json", annotated_edges)
    _write_csv(
        out_path / "kg_edges.csv",
        annotated_edges,
        ["src", "dst", "relation", "source_doc_id", "source_chunk_id", "experiment_ref", "paper_doc_id", "reaction_system", "paper_reaction_system"],
    )
    _write_csv(
        out_path / "paper_reaction_system.csv",
        paper_rows,
        ["doc_id", "doi", "title", "reaction_system", "raw_reaction_system", "confidence", "rationale", "evidence_terms", "status"],
    )
    distribution = dict(Counter(edge["reaction_system"] for edge in annotated_edges))
    paper_distribution = dict(Counter(row["reaction_system"] for row in paper_rows))
    report = {
        "base_kg": str(base_path),
        "output_kg": str(out_path),
        "papers": len(paper_rows),
        "nodes": len(nodes),
        "edges": len(annotated_edges),
        "paper_reaction_system_distribution": paper_distribution,
        "edge_reaction_system_distribution": distribution,
        "inheritance_distribution": {f"{paper}->{edge}": count for (paper, edge), count in sorted(inherited.items())},
        "missing_edge_reaction_system": sum(1 for edge in annotated_edges if not edge.get("reaction_system")),
    }
    _write_json(out_path / "paper_reaction_system_report.json", report)
    _write_markdown_report(out_path / "PAPER_REACTION_SYSTEM_REPORT.md", report)
    return report


def _write_markdown_report(path: Path, report: dict) -> None:
    lines = [
        "# Paper-Level Reaction-System KG Report",
        "",
        f"- Base KG: `{report['base_kg']}`",
        f"- Output KG: `{report['output_kg']}`",
        f"- Papers classified: {report['papers']}",
        f"- Nodes: {report['nodes']}",
        f"- Edges: {report['edges']}",
        f"- Missing edge `reaction_system`: {report['missing_edge_reaction_system']}",
        "",
        "## Paper Distribution",
        "",
        "| label | papers |",
        "|---|---:|",
    ]
    for key, value in sorted(report["paper_reaction_system_distribution"].items()):
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Edge Distribution", "", "| label | edges |", "|---|---:|"])
    for key, value in sorted(report["edge_reaction_system_distribution"].items()):
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Inheritance Distribution", "", "| paper label -> edge label | edges |", "|---|---:|"])
    for key, value in sorted(report["inheritance_distribution"].items()):
        lines.append(f"| {key} | {value} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(
    base_kg_dir: str | Path,
    step1_dir: str | Path,
    chunks_csv: str | Path,
    out_dir: str | Path,
    model: str,
    min_confidence: float,
    concurrency: int,
    limit: int | None = None,
) -> dict:
    base_path = Path(base_kg_dir)
    out_path = Path(out_dir)
    edges = _read_json(base_path / "kg_edges.json")
    if not isinstance(edges, list):
        raise ValueError("kg_edges.json must be a JSON list")
    doc_ids = _edge_doc_ids(edges)
    paper_inputs = load_paper_inputs(step1_dir, chunks_csv, doc_ids)
    paper_rows = classify_papers(paper_inputs, out_path, model=model, min_confidence=min_confidence, concurrency=concurrency, limit=limit)
    if limit is not None:
        limited_ids = {row["doc_id"] for row in paper_rows}
        edges = [edge for edge in edges if edge.get("source_doc_id") in limited_ids]
    return write_annotated_kg(base_path, out_path, paper_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify paper-level reaction systems with GPT and inherit labels to KG edges.")
    parser.add_argument("--base-kg-dir", default=str(DEFAULT_BASE_KG_DIR))
    parser.add_argument("--step1-dir", default=str(DEFAULT_STEP1_DIR))
    parser.add_argument("--chunks-csv", default=str(DEFAULT_CHUNKS_CSV))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--model", default="gpt-5-mini")
    parser.add_argument("--min-confidence", type=float, default=0.55)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    report = run(
        args.base_kg_dir,
        args.step1_dir,
        args.chunks_csv,
        args.out_dir,
        model=args.model,
        min_confidence=args.min_confidence,
        concurrency=args.concurrency,
        limit=args.limit,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
