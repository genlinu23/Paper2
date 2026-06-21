from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from collections import Counter
from pathlib import Path


REACTION_SYSTEMS = ("CO2RR", "CORR", "transferable", "unknown")

CO2_PATTERNS = (
    r"\bco2rr\b",
    r"\bco2\b",
    r"\bco₂\b",
    r"\bcarbon dioxide\b",
    r"\bco2 reduction\b",
    r"\bcarbon dioxide reduction\b",
    r"\bco2 electroreduction\b",
    r"\bco2 electrolysis\b",
    r"\bco2-to-",
    r"\bco₂-to-",
)

CORR_PATTERNS = (
    r"\bcorr\b",
    r"\bco reduction\b",
    r"\bco electroreduction\b",
    r"\bcarbon monoxide reduction\b",
    r"\bco electrolysis\b",
    r"\bco feed\b",
    r"\bco gas\b",
    r"\bcarbon monoxide\b",
    r"\bco-to-",
)

TRANSFERABLE_PATTERNS = (
    r"\bptfe\b",
    r"\bporous diaphragm\b",
    r"\bdiaphragm\b",
    r"\bseparator\b",
    r"\bmembrane\b",
    r"\baem\b",
    r"\bkoh\b",
    r"\bk\+\b",
    r"\bcation\b",
    r"\baerosol\b",
    r"\bspray\b",
    r"\bdroplet\b",
    r"\bflooding\b",
    r"\bdry[- ]?out\b",
    r"\bohmic\b",
    r"\bresistance\b",
    r"\bhfr\b",
    r"\bmass transport\b",
    r"\bgas[- ]liquid[- ]solid\b",
    r"\bgas[- ]aerosol[- ]solid\b",
    r"\bthree[- ]phase\b",
    r"\btriple[- ]phase\b",
    r"\bporous transport layer\b",
    r"\bptl\b",
    r"\bhor\b",
    r"\bhydrogen oxidation\b",
    r"\bh2\b",
)

CO_AMBIGUOUS_RE = re.compile(r"\bco\b")
CO2_RE = re.compile(r"\bco2\b|\bco₂\b|carbon dioxide")
CO_METAL_RE = re.compile(r"\bco[-_/]?(oxide|oh|n|p|s|se|catalyst|phthalocyanine|porphyrin|foam|metal|site|single atom|sac)\b|\bcobalt\b")


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


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


def _pattern_hits(patterns: tuple[str, ...], text: str) -> list[str]:
    return [pattern for pattern in patterns if re.search(pattern, text)]


def classify_reaction_system(text: str) -> tuple[str, dict[str, list[str] | str]]:
    lowered = text.lower()
    co2_hits = _pattern_hits(CO2_PATTERNS, lowered)
    corr_hits = _pattern_hits(CORR_PATTERNS, lowered)
    transferable_hits = _pattern_hits(TRANSFERABLE_PATTERNS, lowered)

    if CO_AMBIGUOUS_RE.search(lowered) and not CO2_RE.search(lowered) and not CO_METAL_RE.search(lowered):
        corr_hits.append(r"\bco\b")

    if corr_hits and not co2_hits:
        label = "CORR"
    elif co2_hits and not corr_hits:
        label = "CO2RR"
    elif corr_hits and co2_hits:
        label = "transferable"
    elif transferable_hits:
        label = "transferable"
    else:
        label = "unknown"
    return label, {
        "co2_hits": co2_hits[:5],
        "corr_hits": corr_hits[:5],
        "transferable_hits": transferable_hits[:5],
    }


def annotate_kg(kg_dir: str | Path, out_dir: str | Path, overwrite: bool = False) -> dict:
    kg_path = Path(kg_dir)
    out_path = Path(out_dir)
    if out_path.exists():
        if not overwrite:
            raise FileExistsError(f"output exists: {out_path}")
        shutil.rmtree(out_path)
    out_path.mkdir(parents=True, exist_ok=True)

    nodes = _read_json(kg_path / "kg_nodes.json")
    edges = _read_json(kg_path / "kg_edges.json")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("kg_nodes.json and kg_edges.json must be JSON lists")
    node_by_id = {node["node_id"]: node for node in nodes}

    annotated_edges: list[dict] = []
    audit_rows: list[dict] = []
    for edge in edges:
        text = _edge_text(edge, node_by_id)
        label, evidence = classify_reaction_system(text)
        annotated = dict(edge)
        annotated["reaction_system"] = label
        annotated_edges.append(annotated)
        audit_rows.append(
            {
                "src": edge.get("src"),
                "dst": edge.get("dst"),
                "relation": edge.get("relation"),
                "source_doc_id": edge.get("source_doc_id"),
                "source_chunk_id": edge.get("source_chunk_id"),
                "reaction_system": label,
                "co2_hits": "; ".join(evidence["co2_hits"]),
                "corr_hits": "; ".join(evidence["corr_hits"]),
                "transferable_hits": "; ".join(evidence["transferable_hits"]),
            }
        )

    for src in kg_path.iterdir():
        if src.name in {"kg_nodes.json", "kg_edges.json", "kg_edges.csv"}:
            continue
        dst = out_path / src.name
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    _write_json(out_path / "kg_nodes.json", nodes)
    _write_json(out_path / "kg_edges.json", annotated_edges)
    edge_fieldnames = ["src", "dst", "relation", "source_doc_id", "source_chunk_id", "experiment_ref", "reaction_system"]
    _write_csv(out_path / "kg_edges.csv", annotated_edges, edge_fieldnames)
    _write_csv(
        out_path / "reaction_system_edge_audit.csv",
        audit_rows,
        ["src", "dst", "relation", "source_doc_id", "source_chunk_id", "reaction_system", "co2_hits", "corr_hits", "transferable_hits"],
    )

    distribution = dict(Counter(edge["reaction_system"] for edge in annotated_edges))
    report = {
        "input_kg": str(kg_path),
        "output_kg": str(out_path),
        "nodes": len(nodes),
        "edges": len(annotated_edges),
        "reaction_system_distribution": {system: distribution.get(system, 0) for system in REACTION_SYSTEMS},
        "missing_reaction_system": sum(1 for edge in annotated_edges if not edge.get("reaction_system")),
    }
    _write_json(out_path / "reaction_system_report.json", report)
    _write_markdown_report(out_path / "REACTION_SYSTEM_REPORT.md", report, audit_rows)
    return report


def _write_markdown_report(path: Path, report: dict, audit_rows: list[dict]) -> None:
    distribution = report["reaction_system_distribution"]
    lines = [
        "# KG Reaction-System Annotation Report",
        "",
        f"- Input KG: `{report['input_kg']}`",
        f"- Output KG: `{report['output_kg']}`",
        f"- Nodes: {report['nodes']}",
        f"- Edges: {report['edges']}",
        f"- Missing `reaction_system`: {report['missing_reaction_system']}",
        "",
        "## Distribution",
        "",
        "| reaction_system | edges |",
        "|---|---:|",
    ]
    for system in REACTION_SYSTEMS:
        lines.append(f"| {system} | {distribution.get(system, 0)} |")
    lines.extend(["", "## Samples", ""])
    for system in REACTION_SYSTEMS:
        lines.extend([f"### {system}", "", "| src | relation | dst | doc | chunk | hits |", "|---|---|---|---|---|---|"])
        examples = [row for row in audit_rows if row["reaction_system"] == system][:5]
        if not examples:
            lines.append("| none | | | | | |")
        for row in examples:
            hits = "; ".join(item for item in (row["co2_hits"], row["corr_hits"], row["transferable_hits"]) if item)
            lines.append(
                f"| {row['src']} | {row['relation']} | {row['dst']} | {row['source_doc_id']} | {row['source_chunk_id']} | {hits} |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Annotate every KG edge with a reaction_system label.")
    parser.add_argument("--kg-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    report = annotate_kg(args.kg_dir, args.out_dir, overwrite=args.overwrite)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
