from __future__ import annotations

import csv
import json
import sqlite3
import time
import traceback
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .. import llm as llm_client
from ..contracts import (
    ChunkInputRecord,
    CorePaperSummary,
    Fact,
    LiteratureDBStats,
    LiteratureFactType,
    LiteratureSource,
    PaperFacts,
)


TOPIC_KEYWORDS: dict[LiteratureFactType, tuple[str, ...]] = {
    LiteratureFactType.STRUCTURE: ("cell", "electrode", "membrane", "separator", "porous", "flow field", "gde", "ptl", "aem"),
    LiteratureFactType.REACTION: ("reaction", "cathode", "anode", "electrolysis", "co2", "h2", "oer", "her"),
    LiteratureFactType.MEMBRANE: ("membrane", "separator", "diaphragm", "aem", "pem", "ion exchange"),
    LiteratureFactType.FEED: ("feed", "electrolyte", "koh", "solution", "gas", "liquid", "aerosol"),
    LiteratureFactType.PERFORMANCE: ("performance", "faradaic", "selectivity", "yield", "current density", "voltage", "stability"),
    LiteratureFactType.FAILURE: ("failure", "flooding", "dry", "degradation", "salt", "block", "short", "crack"),
}

CHUNK_INPUT_FIELDS = tuple(ChunkInputRecord.model_fields)
DEFAULT_LIBRARY_ROOT = Path(r"C:\Users\logan\Desktop\project2_strict")
DEFAULT_CORE_ROOT = Path(r"C:\Users\logan\Desktop\project2_strict_workspace_archive_20260617\core")
DEFAULT_ANCHOR_DOIS = [
    "10.1038/s41586-023-06792-0",
    "10.1038/s41560-020-00761-x",
    "10.1038/s41560-019-0451-x",
    "10.1038/s41467-020-17403-1",
    "10.1038/s41467-023-43300-4",
    "10.1038/s41586-023-05918-8",
    "10.1002/cssc.201902547",
    "10.1021/acs.chemrev.3c00206",
]
PDF_MANIFEST = Path("doi_pdf_filter_audit_v1") / "pdf_manifest.csv"
DOI_METADATA = Path("doi_pdf_filter_audit_v1") / "unique_doi_metadata.csv"
FULL_CHUNK_RUN = "final_chunk_run_v1"
CORE_CHUNK_RUN = "chunk_run_v1"
EXTRACTION_BATCH_CHAR_BUDGET = 45_000
DEFAULT_BATCH_LIBS = ["lib1", "lib2", "lib3", "lib4", "lib5"]
DEFAULT_BATCH_CLASSES = ["classA", "classB"]
REACTOR_KEEP_KEYWORDS = (
    "reactor",
    "electrolyzer",
    "electrolysis",
    "gde",
    "gas diffusion",
    "gas-diffusion",
    "flow cell",
    "flow-cell",
    "membrane",
    "bipolar membrane",
    "anion exchange membrane",
    "aem",
    "ptl",
    "ptfe",
    "spray",
    "flood",
    "dry-out",
    "carbonation",
    "crossover",
    "diagnos",
    "stability",
    "durability",
    "selectivity",
    "current density",
    "faradaic",
)
REACTOR_DROP_KEYWORDS = (
    "photocatal",
    "photocatalysis",
    "photochemical",
    "bio-inspired",
    "wettability",
    "fog collection",
    "crystallization",
    "protein",
    "enzyme",
    "hydrogenase",
    "proton memory",
    "superhydrophobic",
    "corrosion",
)


def _default_library_root() -> Path:
    return Path(__import__("os").environ.get("REACTOR_LIBRARY_ROOT", str(DEFAULT_LIBRARY_ROOT)))


def _normalize_doi(value: str) -> str:
    doi = value.strip().lower()
    if doi.startswith("https://doi.org/"):
        doi = doi.removeprefix("https://doi.org/")
    if doi.startswith("doi:"):
        doi = doi.removeprefix("doi:")
    return doi


def _pdf_key_from_doi(doi: str) -> str:
    return _normalize_doi(doi).replace("/", "_")


def _pdf_key_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    parts = stem.split("_", 1)
    if len(parts) == 2 and parts[0].isdigit() and parts[1].startswith("10."):
        stem = parts[1]
    if not stem.startswith("10."):
        raise ValueError(f"filename does not contain a DOI-like pdf_key: {filename}")
    return stem.lower()


def _doi_from_pdf_key(pdf_key: str) -> str:
    key = pdf_key.strip().lower()
    if "_" not in key:
        return key
    prefix, suffix = key.split("_", 1)
    return f"{prefix}/{suffix}"


def _resolve_roots(library_root: str | Path | None = None) -> tuple[Path, Path]:
    root = Path(library_root) if library_root is not None else _default_library_root()
    if (root / "03_text_chunks" / "body_chunks.csv").exists():
        return root.parent, root
    for name in (FULL_CHUNK_RUN, CORE_CHUNK_RUN):
        candidate = root / name
        if (candidate / "03_text_chunks" / "body_chunks.csv").exists():
            return root, candidate
    raise FileNotFoundError(f"chunk run with 03_text_chunks/body_chunks.csv not found under: {root}")


def _chunk_root(library_root: str | Path | None = None) -> Path:
    return _resolve_roots(library_root)[1]


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"required CSV not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return [dict(row) for row in csv.DictReader(fh)]


def _metadata_by_doi(library_root: Path) -> dict[str, dict[str, str]]:
    metadata: dict[str, dict[str, str]] = {}
    metadata_path = library_root / DOI_METADATA
    if metadata_path.exists():
        for row in _read_csv_rows(metadata_path):
            doi = _normalize_doi(row.get("doi", ""))
            if doi:
                metadata[doi] = row
    web_input = library_root / "web_input.csv"
    if web_input.exists():
        for row in _read_csv_rows(web_input):
            doi = _normalize_doi(row.get("doi", ""))
            if doi:
                metadata.setdefault(doi, row)
    return metadata


def _pdf_manifest_rows(library_root: Path) -> list[dict[str, str]]:
    manifest_path = library_root / PDF_MANIFEST
    if not manifest_path.exists():
        return []
    rows = _read_csv_rows(manifest_path)
    required = {"pdf_key", "doi", "lib", "class_name"}
    headers = set(rows[0]) if rows else set()
    if not required.issubset(headers):
        raise ValueError(f"pdf manifest missing required columns {sorted(required)}: {manifest_path}")
    return rows


def _corpus_index(chunk_run: Path) -> dict[str, dict[str, str]]:
    corpus_path = chunk_run / "02_corpus_index" / "corpus_index.csv"
    rows = _read_csv_rows(corpus_path)
    required = {"doc_id", "filename"}
    headers = set(rows[0]) if rows else set()
    if not required.issubset(headers):
        raise ValueError(f"corpus index missing required columns {sorted(required)}: {corpus_path}")
    return {row["doc_id"].strip(): row for row in rows if row.get("doc_id")}


def _doc_lookup(library_root: Path, chunk_run: Path) -> dict[str, dict[str, str | None]]:
    manifest_by_key = {_pdf_key_from_doi(row["doi"]): row for row in _pdf_manifest_rows(library_root)}
    metadata = _metadata_by_doi(library_root)
    lookup: dict[str, dict[str, str | None]] = {}
    for doc_id, row in _corpus_index(chunk_run).items():
        pdf_key = _pdf_key_from_filename(row["filename"])
        manifest_row = manifest_by_key.get(pdf_key)
        doi = _normalize_doi(manifest_row["doi"]) if manifest_row else _doi_from_pdf_key(pdf_key)
        meta = metadata.get(doi, {})
        lookup[doc_id] = {
            "doc_id": doc_id,
            "filename": row["filename"],
            "pdf_key": pdf_key,
            "doi": doi,
            "title": (meta.get("title") or "").strip() or None,
            "lib": manifest_row.get("lib") if manifest_row else None,
            "class_name": manifest_row.get("class_name") if manifest_row else None,
        }
    return lookup


def _normalize_text(value: object, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing text: {context}")
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def _load_manifest(library_dir: Path) -> dict[str, dict[str, str | None]]:
    manifest_dir = library_dir / "manifests"
    if not manifest_dir.exists():
        raise FileNotFoundError(f"required manifest directory not found: {manifest_dir}")

    csv_paths = sorted(manifest_dir.glob("source_json_deduped_*.csv"))
    if not csv_paths:
        raise FileNotFoundError(f"required manifest CSV not found under: {manifest_dir}")

    manifest: dict[str, dict[str, str | None]] = {}
    for csv_path in csv_paths:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            required = {"doc_id", "doi", "title"}
            headers = set(reader.fieldnames or [])
            if not required.issubset(headers):
                raise ValueError(f"manifest missing required columns {sorted(required)}: {csv_path}")
            for row_num, row in enumerate(reader, start=2):
                doc_id = (row["doc_id"] or "").strip()
                title = (row["title"] or "").strip()
                doi = (row["doi"] or "").strip()
                if not doc_id or not title:
                    raise ValueError(f"manifest row {row_num} missing doc_id/title: {csv_path}")
                manifest[doc_id] = {"title": title, "doi": doi or None}

    if not manifest:
        raise ValueError(f"manifest contains no documents: {manifest_dir}")
    return manifest


def _iter_json_docs(library_dir: Path) -> Iterable[Path]:
    parsed_dir = library_dir / "parsed"
    if not parsed_dir.exists():
        raise FileNotFoundError(f"required parsed directory not found: {parsed_dir}")
    json_paths = sorted(parsed_dir.glob("doc_*.json"))
    if not json_paths:
        raise FileNotFoundError(f"required parsed/doc_*.json files not found: {parsed_dir}")
    yield from json_paths


def _extract_blocks(payload: object) -> list[dict]:
    candidates: list[dict] = []
    stack: list[object] = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if "text" in current or "content" in current or "raw_text" in current or "lines" in current:
                candidates.append(current)
            for value in current.values():
                if isinstance(value, dict):
                    stack.append(value)
                elif isinstance(value, list):
                    stack.extend(value)
        elif isinstance(current, list):
            stack.extend(current)
        elif isinstance(current, str) and current.strip():
            candidates.append({"text": current})
    return candidates


def _block_text(block: dict, source: Path, block_idx: int) -> str:
    for key in ("text", "content", "raw_text", "value"):
        value = block.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize_text(value, f"{source} block {block_idx}")
    if isinstance(block.get("lines"), list):
        pieces = []
        for item in block["lines"]:
            if not isinstance(item, dict):
                raise ValueError(f"invalid line item in {source} block {block_idx}")
            txt = item.get("text") or item.get("content")
            if not isinstance(txt, str) or not txt.strip():
                raise ValueError(f"missing line text in {source} block {block_idx}")
            pieces.append(txt.strip())
        return _normalize_text(" ".join(pieces), f"{source} block {block_idx}")
    raise ValueError(f"readable text not found in {source} block {block_idx}")


def _split_chunks(text: str, max_words: int = 220) -> list[str]:
    words = text.split()
    if not words:
        raise ValueError("cannot chunk empty text")
    return [" ".join(words[i : i + max_words]).strip() for i in range(0, len(words), max_words)]


def _validate_chunk_record(row: dict, source: str) -> ChunkInputRecord:
    missing = [field for field in CHUNK_INPUT_FIELDS if field not in row]
    if missing:
        raise ValueError(f"chunk input missing required fields {missing}: {source}")
    return ChunkInputRecord.model_validate(row)


def load_chunk_records(chunk_file: str | Path) -> list[ChunkInputRecord]:
    path = Path(chunk_file)
    if not path.exists():
        raise FileNotFoundError(f"chunk file not found: {path}")
    if path.suffix.lower() == ".jsonl":
        records = []
        with path.open("r", encoding="utf-8") as fh:
            for line_num, line in enumerate(fh, start=1):
                if not line.strip():
                    raise ValueError(f"empty JSONL line is not allowed: {path}:{line_num}")
                payload = json.loads(line)
                if not isinstance(payload, dict):
                    raise ValueError(f"JSONL line must be an object: {path}:{line_num}")
                records.append(_validate_chunk_record(payload, f"{path}:{line_num}"))
        if not records:
            raise ValueError(f"chunk file contains no records: {path}")
        return records

    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            headers = set(reader.fieldnames or [])
            missing = [field for field in CHUNK_INPUT_FIELDS if field not in headers]
            if missing:
                raise ValueError(f"chunk CSV missing required fields {missing}: {path}")
            records = [_validate_chunk_record(row, f"{path}:{row_num}") for row_num, row in enumerate(reader, start=2)]
        if not records:
            raise ValueError(f"chunk file contains no records: {path}")
        return records

    if path.suffix.lower() == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError(f"chunk JSON must be a list of objects: {path}")
        records = []
        for idx, item in enumerate(payload, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"chunk JSON item must be an object: {path}[{idx}]")
            records.append(_validate_chunk_record(item, f"{path}[{idx}]"))
        if not records:
            raise ValueError(f"chunk file contains no records: {path}")
        return records

    raise ValueError(f"unsupported chunk file extension: {path.suffix}")


def select_by_group(lib: str, classes: list[str], oa_only: bool = False, library_root: str | Path | None = None) -> list[str]:
    """Return DOI values selected deterministically from the physical lib x class grouping."""
    if not lib:
        raise ValueError("lib is required")
    if not classes:
        raise ValueError("classes is required")
    if oa_only:
        raise ValueError("oa_only cannot be applied: pdf_manifest.csv has no explicit OA/non-OA column.")

    root = Path(library_root) if library_root is not None else _default_library_root()
    rows = _pdf_manifest_rows(root)
    wanted_classes = {item.strip() for item in classes if item.strip()}
    if not wanted_classes:
        raise ValueError("classes contains no usable class names")

    selected: list[str] = []
    seen: set[str] = set()
    for row in rows:
        if row.get("lib", "").strip() != lib:
            continue
        if row.get("class_name", "").strip() not in wanted_classes:
            continue
        doi = _normalize_doi(row.get("doi", ""))
        if not doi:
            raise ValueError(f"pdf manifest row selected but DOI is empty: lib={lib}, classes={classes}")
        if doi not in seen:
            selected.append(doi)
            seen.add(doi)
    return selected


def _load_chunks_from_library(doc_ids_or_dois: list[str], library_root: str | Path | None = None) -> list[dict]:
    if not doc_ids_or_dois:
        raise ValueError("doc_ids_or_dois is required")
    root, chunk_run = _resolve_roots(library_root)
    lookup = _doc_lookup(root, chunk_run)

    wanted_doc_ids: set[str] = set()
    wanted_dois = {_normalize_doi(item) for item in doc_ids_or_dois if item and not item.startswith("doc_")}
    explicit_doc_ids = {item for item in doc_ids_or_dois if item.startswith("doc_")}
    for doc_id, meta in lookup.items():
        if doc_id in explicit_doc_ids or meta["doi"] in wanted_dois:
            wanted_doc_ids.add(doc_id)

    missing_doc_ids = sorted(explicit_doc_ids - set(lookup))
    matched_dois = {lookup[doc_id]["doi"] for doc_id in wanted_doc_ids}
    missing_dois = sorted(wanted_dois - matched_dois)
    if missing_doc_ids or missing_dois:
        raise ValueError(f"requested documents not found in corpus index: doc_ids={missing_doc_ids}, dois={missing_dois}")

    chunks_path = chunk_run / "03_text_chunks" / "body_chunks.csv"
    rows = _read_csv_rows(chunks_path)
    if not rows:
        raise ValueError(f"body chunk CSV contains no rows: {chunks_path}")
    missing_fields = [field for field in CHUNK_INPUT_FIELDS if field not in rows[0]]
    if missing_fields:
        raise ValueError(f"body chunk CSV missing required fields {missing_fields}: {chunks_path}")

    chunks: list[dict] = []
    for row in rows:
        doc_id = row.get("doc_id", "").strip()
        if doc_id not in wanted_doc_ids:
            continue
        record = ChunkInputRecord.model_validate(row)
        meta = lookup[doc_id]
        data = record.model_dump()
        data.update(
            {
                "doi": meta["doi"],
                "title": meta["title"],
                "lib": meta["lib"],
                "class_name": meta["class_name"],
                "pdf_key": meta["pdf_key"],
            }
        )
        chunks.append(data)

    found_doc_ids = {chunk["doc_id"] for chunk in chunks}
    empty_doc_ids = sorted(wanted_doc_ids - found_doc_ids)
    if empty_doc_ids:
        raise ValueError(f"requested documents have no body chunks: {empty_doc_ids}")
    return chunks


def build_literature_db_from_chunks(chunk_file: str, out_dir: str) -> dict:
    records = load_chunk_records(chunk_file)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    db_path = out_path / "literature.db"

    docs: dict[str, dict] = {}
    with sqlite3.connect(db_path) as con:
        con.execute("DROP TABLE IF EXISTS chunks")
        con.execute("DROP TABLE IF EXISTS paper_summary")
        con.execute(
            """
            CREATE TABLE chunks (
                doc_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                page_num INTEGER NOT NULL,
                text TEXT NOT NULL,
                title TEXT NOT NULL,
                doi TEXT,
                source_path TEXT NOT NULL,
                paragraph_id TEXT NOT NULL,
                char_start INTEGER NOT NULL,
                char_end INTEGER NOT NULL,
                section_title TEXT NOT NULL,
                chunk_type TEXT NOT NULL,
                source_block_type TEXT NOT NULL,
                source_block_id INTEGER NOT NULL,
                PRIMARY KEY (doc_id, chunk_id)
            )
            """
        )
        con.execute(
            """
            CREATE TABLE paper_summary (
                doc_id TEXT PRIMARY KEY,
                doi TEXT,
                title TEXT NOT NULL,
                chunk_count INTEGER NOT NULL,
                topic_signal_count INTEGER NOT NULL,
                score REAL NOT NULL,
                anchor INTEGER NOT NULL,
                summary_json TEXT NOT NULL
            )
            """
        )

        seen_chunks: set[tuple[str, str]] = set()
        for record in records:
            key = (record.doc_id, record.chunk_id)
            if key in seen_chunks:
                raise ValueError(f"duplicate chunk_id for doc_id={record.doc_id}: {record.chunk_id}")
            seen_chunks.add(key)
            if record.char_end < record.char_start:
                raise ValueError(f"char_end < char_start for {record.doc_id}/{record.chunk_id}")

            text = record.clean_text.strip()
            if not text:
                raise ValueError(f"clean_text is empty for {record.doc_id}/{record.chunk_id}")

            title = record.section_title.strip()
            if not title:
                raise ValueError(f"section_title is empty for {record.doc_id}/{record.chunk_id}")

            con.execute(
                """
                INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.doc_id,
                    record.chunk_id,
                    record.page_number,
                    text,
                    title,
                    None,
                    record.filename,
                    record.paragraph_id,
                    record.char_start,
                    record.char_end,
                    record.section_title,
                    record.chunk_type,
                    record.source_block_type,
                    record.source_block_id,
                ),
            )

            doc = docs.setdefault(
                record.doc_id,
                {
                    "doc_id": record.doc_id,
                    "title": record.section_title,
                    "doi": None,
                    "source_path": record.filename,
                    "chunk_count": 0,
                    "text_chars": 0,
                    "topic_signals": 0,
                },
            )
            doc["chunk_count"] += 1
            doc["text_chars"] += len(text)
            doc["topic_signals"] += sum(
                1 for keywords in TOPIC_KEYWORDS.values() if any(keyword in text.lower() for keyword in keywords)
            )

        for doc in docs.values():
            score = doc["topic_signals"] * 2 + min(doc["chunk_count"], 20)
            con.execute(
                "INSERT INTO paper_summary VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    doc["doc_id"],
                    doc["doi"],
                    doc["title"],
                    doc["chunk_count"],
                    doc["topic_signals"],
                    float(score),
                    0,
                    json.dumps(doc, ensure_ascii=False),
                ),
            )
        con.commit()

    stats = LiteratureDBStats(
        n_docs=len(docs),
        n_chunks=len(records),
        tags=sorted(fact_type.value for fact_type in LiteratureFactType),
        db_path=str(db_path),
    )
    (out_path / "literature_manifest.json").write_text(
        json.dumps({"stats": stats.model_dump(), "docs": list(docs.values())}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return stats.model_dump()


def _metadata_from_chunk_filename(filename: str) -> dict[str, str | None]:
    stem = Path(filename).stem
    parts = stem.split("__", 2)
    if len(parts) != 3:
        return {"lib": None, "class_name": None, "doi": None, "title": stem}
    lib, class_name, doi_key = parts
    doi = doi_key.replace("_", "/", 1)
    return {"lib": lib, "class_name": class_name, "doi": doi, "title": doi}


def _chunk_record_to_extraction_dict(record: ChunkInputRecord) -> dict[str, str | int | None]:
    metadata = _metadata_from_chunk_filename(record.filename)
    return {
        "doc_id": record.doc_id,
        "filename": record.filename,
        "page_number": record.page_number,
        "paragraph_id": record.paragraph_id,
        "chunk_id": record.chunk_id,
        "char_start": record.char_start,
        "char_end": record.char_end,
        "text": record.text,
        "clean_text": record.clean_text,
        "section_title": record.section_title,
        "chunk_type": record.chunk_type,
        "source_block_type": record.source_block_type,
        "source_block_id": record.source_block_id,
        **metadata,
    }


def run_step1_chunk_file_extraction(
    chunk_file: str | Path,
    out_dir: str | Path,
    concurrency: int = 8,
    max_retries: int = 2,
    retry_sleep_s: float = 3.0,
    join_only: bool = False,
    overwrite: bool = False,
    limit: int | None = None,
) -> dict:
    if concurrency < 1:
        raise ValueError("concurrency must be >= 1")
    if max_retries < 0:
        raise ValueError("max_retries must be >= 0")
    if limit is not None and limit < 1:
        raise ValueError("limit must be >= 1")

    records = load_chunk_records(chunk_file)
    chunks = [_chunk_record_to_extraction_dict(record) for record in records]
    grouped = _group_chunks_by_doc(chunks)
    if limit is not None:
        grouped = dict(list(grouped.items())[:limit])
    core_papers = _core_paper_records(grouped)

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    join_manifest = {
        "chunk_file": str(Path(chunk_file)),
        "core_papers": core_papers,
        "doc_count": len(grouped),
        "chunk_count": sum(len(doc_chunks) for doc_chunks in grouped.values()),
        "concurrency": concurrency,
        "max_retries": max_retries,
    }
    _write_json(out_path / "chunk_join_manifest.json", join_manifest)
    _write_json(out_path / "core_papers.json", core_papers)

    if join_only:
        output = {
            "core_papers": core_papers,
            "paper_facts": [],
            "failures": [],
            "output_dir": str(out_path),
            "join_only": True,
        }
        _write_json(out_path / "step1_output.json", output)
        return output

    paper_dir = out_path / "paper_facts_by_doc"
    paper_dir.mkdir(parents=True, exist_ok=True)
    failures: list[dict] = []
    paper_facts: list[PaperFacts] = []
    completed = 0
    total = len(grouped)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(
                _extract_doc_with_retry,
                doc_id,
                doc_chunks,
                paper_dir,
                max_retries,
                retry_sleep_s,
                overwrite,
            ): doc_id
            for doc_id, doc_chunks in grouped.items()
        }
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            status = result["status"]
            if status in {"ok", "skipped"}:
                paper_facts.append(result["paper_facts"])
            else:
                failures.append({k: v for k, v in result.items() if k != "paper_facts"})
            if completed == total or completed % 10 == 0:
                checkpoint = {
                    "completed": completed,
                    "total": total,
                    "success_or_skipped": len(paper_facts),
                    "failed": len(failures),
                    "last_doc_id": result["doc_id"],
                }
                _write_json(out_path / "progress.json", checkpoint)
                _write_batch_outputs(out_path, core_papers, paper_facts, failures)

    return _write_batch_outputs(out_path, core_papers, paper_facts, failures)


def build_literature_db(library_dir: str, out_dir: str) -> dict:
    library_path = Path(library_dir)
    if not library_path.exists():
        raise FileNotFoundError(f"library_dir not found: {library_path}")
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    db_path = out_path / "literature.db"

    manifest = _load_manifest(library_path)
    docs: list[dict] = []
    total_chunks = 0

    with sqlite3.connect(db_path) as con:
        con.execute("DROP TABLE IF EXISTS chunks")
        con.execute("DROP TABLE IF EXISTS paper_summary")
        con.execute(
            """
            CREATE TABLE chunks (
                doc_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                page_num INTEGER,
                text TEXT NOT NULL,
                title TEXT NOT NULL,
                doi TEXT,
                source_path TEXT NOT NULL,
                PRIMARY KEY (doc_id, chunk_id)
            )
            """
        )
        con.execute(
            """
            CREATE TABLE paper_summary (
                doc_id TEXT PRIMARY KEY,
                doi TEXT,
                title TEXT NOT NULL,
                chunk_count INTEGER NOT NULL,
                topic_signal_count INTEGER NOT NULL,
                score REAL NOT NULL,
                anchor INTEGER NOT NULL,
                summary_json TEXT NOT NULL
            )
            """
        )

        parsed_docs = list(_iter_json_docs(library_path))
        for json_path in parsed_docs:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            doc_id = json_path.stem
            if doc_id not in manifest:
                raise ValueError(f"parsed document has no manifest row: {json_path}")
            title = manifest[doc_id]["title"]
            doi = manifest[doc_id]["doi"]

            blocks = _extract_blocks(payload)
            if not blocks:
                raise ValueError(f"parsed document has no readable blocks: {json_path}")

            chunk_total = 0
            text_total = 0
            topic_signal_total = 0
            for block_idx, block in enumerate(blocks, start=1):
                text = _block_text(block, json_path, block_idx)
                page_num = block.get("page_num")
                if isinstance(page_num, str) and page_num.isdigit():
                    page_num = int(page_num)
                if page_num is not None and not isinstance(page_num, int):
                    raise ValueError(f"invalid page_num in {json_path} block {block_idx}")

                for piece_idx, chunk_text in enumerate(_split_chunks(text), start=1):
                    chunk_id = f"{block_idx:04d}_{piece_idx:02d}"
                    con.execute(
                        "INSERT OR REPLACE INTO chunks VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (doc_id, chunk_id, page_num, chunk_text, title, doi, str(json_path)),
                    )
                    chunk_total += 1
                    text_total += len(chunk_text)
                    topic_signal_total += sum(
                        1
                        for keywords in TOPIC_KEYWORDS.values()
                        if any(keyword in chunk_text.lower() for keyword in keywords)
                    )

            if chunk_total == 0:
                raise ValueError(f"parsed document produced zero chunks: {json_path}")

            score = topic_signal_total * 2 + min(chunk_total, 20)
            summary = {
                "doc_id": doc_id,
                "title": title,
                "doi": doi,
                "chunk_count": chunk_total,
                "text_chars": text_total,
                "topic_signals": topic_signal_total,
                "source_path": str(json_path),
            }
            con.execute(
                "INSERT OR REPLACE INTO paper_summary VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (doc_id, doi, title, chunk_total, topic_signal_total, float(score), 0, json.dumps(summary, ensure_ascii=False)),
            )
            docs.append(summary)
            total_chunks += chunk_total
        con.commit()

    stats = LiteratureDBStats(
        n_docs=len(docs),
        n_chunks=total_chunks,
        tags=sorted(fact_type.value for fact_type in LiteratureFactType),
        db_path=str(db_path),
    )
    (out_path / "literature_manifest.json").write_text(
        json.dumps({"stats": stats.model_dump(), "docs": docs}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return stats.model_dump()


def select_core_papers(library_db: str, anchors: list[LiteratureSource], min_count: int = 30) -> list[CorePaperSummary]:
    db_path = Path(library_db)
    if db_path.is_dir():
        db_path = db_path / "literature.db"
    if not db_path.exists():
        raise FileNotFoundError(f"literature database not found: {db_path}")

    anchor_ids = {item.doc_id for item in anchors}
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT doc_id, doi, title, chunk_count, topic_signal_count, score, anchor
        FROM paper_summary
        ORDER BY score DESC, chunk_count DESC, doc_id
        """
    ).fetchall()
    if len(rows) < min_count:
        raise ValueError(f"not enough papers for core selection: found {len(rows)}, required {min_count}")

    selected: dict[str, CorePaperSummary] = {}
    for row in rows:
        doc_id = row["doc_id"]
        is_anchor = bool(row["anchor"]) or doc_id in anchor_ids
        if len(selected) < min_count or is_anchor:
            selected[doc_id] = CorePaperSummary(
                doc_id=doc_id,
                title=row["title"],
                doi=row["doi"],
                score=float(row["score"]),
                reason=f"score={row['score']:.1f}; chunks={row['chunk_count']}; topic_signals={row['topic_signal_count']}",
                anchor=is_anchor,
            )
    return sorted(selected.values(), key=lambda item: (-item.score, item.doc_id))


def _chunk_text_for_extraction(chunk: dict, chunk_id: str) -> str:
    text_value = chunk.get("clean_text")
    if not isinstance(text_value, str) or not text_value.strip():
        text_value = chunk.get("text")
    return _normalize_text(text_value, f"chunk {chunk_id}")


def _doi_for_chunks(doc_id: str, chunks: list[dict], doi: str | None = None) -> str:
    if doi:
        return _normalize_doi(doi)
    chunk_dois = {_normalize_doi(chunk["doi"]) for chunk in chunks if isinstance(chunk.get("doi"), str) and chunk["doi"].strip()}
    if len(chunk_dois) == 1:
        return next(iter(chunk_dois))
    if not chunk_dois:
        raise ValueError(f"doi is required when chunks do not include DOI for doc_id={doc_id}")
    raise ValueError(f"chunks include multiple DOI values for doc_id={doc_id}: {sorted(chunk_dois)}")


def _validate_paper_facts(result: PaperFacts, doc_id: str, doi: str, chunks: list[dict]) -> None:
    if result.doc_id != doc_id:
        raise ValueError(f"LLM returned mismatched doc_id: expected {doc_id}, got {result.doc_id}")
    if _normalize_doi(result.doi) != doi:
        raise ValueError(f"LLM returned mismatched doi: expected {doi}, got {result.doi}")

    allowed_chunk_ids = {chunk["chunk_id"] for chunk in chunks}
    alias_to_chunk_id: dict[str, str] = {}
    for chunk_id in allowed_chunk_ids:
        prefix, sep, number = chunk_id.rpartition("_")
        if sep and number.isdigit():
            alias_to_chunk_id[f"{prefix}_{int(number)}"] = chunk_id
    for field_name in ("structure", "reaction", "membrane", "feed", "performance", "failure"):
        facts = getattr(result, field_name)
        if not facts:
            raise ValueError(f"LLM returned empty fact list for {field_name}")
        for fact in facts:
            if fact.value == "not_mentioned":
                if fact.chunk_id is not None:
                    raise ValueError(f"not_mentioned fact must use chunk_id=None: {field_name}")
                continue
            if not fact.chunk_id:
                raise ValueError(f"mentioned fact must include chunk_id: {field_name}")
            if fact.chunk_id not in allowed_chunk_ids and fact.chunk_id in alias_to_chunk_id:
                fact.chunk_id = alias_to_chunk_id[fact.chunk_id]
            if fact.chunk_id not in allowed_chunk_ids:
                raise ValueError(f"fact references unknown chunk_id: {fact.chunk_id}")


def _batch_chunks_for_extraction(chunks: list[dict[str, str]], char_budget: int = EXTRACTION_BATCH_CHAR_BUDGET) -> list[list[dict[str, str]]]:
    if char_budget <= 0:
        raise ValueError("char_budget must be positive")
    batches: list[list[dict[str, str]]] = []
    current: list[dict[str, str]] = []
    current_chars = 0
    for chunk in chunks:
        chunk_chars = len(chunk["clean_text"])
        if current and current_chars + chunk_chars > char_budget:
            batches.append(current)
            current = []
            current_chars = 0
        current.append(chunk)
        current_chars += chunk_chars
    if current:
        batches.append(current)
    return batches


def _merge_fact_lists(facts: list[Fact]) -> list[Fact]:
    mentioned = [fact for fact in facts if fact.value != "not_mentioned"]
    if mentioned:
        return mentioned
    return [Fact(value="not_mentioned", chunk_id=None, section_title=None)]


def _merge_paper_facts(doc_id: str, doi: str, parts: list[PaperFacts]) -> PaperFacts:
    if not parts:
        raise ValueError("cannot merge zero PaperFacts results")
    return PaperFacts(
        doc_id=doc_id,
        doi=doi,
        structure=_merge_fact_lists([fact for part in parts for fact in part.structure]),
        reaction=_merge_fact_lists([fact for part in parts for fact in part.reaction]),
        membrane=_merge_fact_lists([fact for part in parts for fact in part.membrane]),
        feed=_merge_fact_lists([fact for part in parts for fact in part.feed]),
        performance=_merge_fact_lists([fact for part in parts for fact in part.performance]),
        failure=_merge_fact_lists([fact for part in parts for fact in part.failure]),
    )


def extract_paper_facts(doc_id: str, chunks: list[dict], doi: str | None = None) -> PaperFacts:
    if not doc_id:
        raise ValueError("doc_id is required")
    if not chunks:
        raise ValueError(f"no chunks provided for doc_id={doc_id}")

    normalized_chunks: list[dict[str, str]] = []
    for chunk in chunks:
        chunk_id = chunk.get("chunk_id")
        if not isinstance(chunk_id, str) or not chunk_id.strip():
            raise ValueError(f"chunk missing chunk_id for doc_id={doc_id}")
        section_title = chunk.get("section_title")
        if section_title is None:
            section_title = ""
        if not isinstance(section_title, str):
            raise ValueError(f"chunk section_title must be a string for {doc_id}/{chunk_id}")
        text = _chunk_text_for_extraction(chunk, chunk_id)
        normalized_chunks.append({"chunk_id": chunk_id, "section_title": section_title, "clean_text": text})

    paper_doi = _doi_for_chunks(doc_id, chunks, doi)

    system = (
        "You are a literature fact extractor. Use only the provided paper body chunks. "
        "Extract six design-relevant fact classes: structure, reaction, membrane, feed, "
        "performance, failure. Each fact must cite the supporting chunk_id and "
        "section_title. Copy chunk_id exactly, including leading zeros. If a class is not mentioned, return one Fact with "
        "value='not_mentioned', chunk_id=null, section_title=null. Do not invent "
        "DOIs, numbers, conclusions, or references. Do not treat bibliography entries "
        "as facts."
    )
    extractions: list[PaperFacts] = []
    batches = _batch_chunks_for_extraction(normalized_chunks)
    chunks_by_id = {chunk["chunk_id"]: chunk for chunk in chunks}
    for batch_num, batch in enumerate(batches, start=1):
        user = json.dumps(
            {
                "doc_id": doc_id,
                "doi": paper_doi,
                "batch": {"index": batch_num, "count": len(batches)},
                "chunks": batch,
            },
            ensure_ascii=False,
        )
        extraction = llm_client.call(role="literature", system=system, user=user, schema=PaperFacts)
        batch_source_chunks = [chunks_by_id[chunk["chunk_id"]] for chunk in batch]
        _validate_paper_facts(extraction, doc_id, paper_doi, batch_source_chunks)
        extractions.append(extraction)
    return _merge_paper_facts(doc_id, paper_doi, extractions)


def _load_chunks_from_db(db_path: str | Path, doc_id: str | None = None) -> list[dict]:
    path = Path(db_path)
    if path.is_dir():
        path = path / "literature.db"
    if not path.exists():
        raise FileNotFoundError(f"literature database not found: {path}")
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    if doc_id:
        rows = con.execute("SELECT * FROM chunks WHERE doc_id = ? ORDER BY chunk_id", (doc_id,)).fetchall()
    else:
        rows = con.execute("SELECT * FROM chunks ORDER BY doc_id, chunk_id").fetchall()
    return [dict(row) for row in rows]


def load_chunks(source: str | Path | list[str], doc_id: str | None = None, library_root: str | Path | None = None) -> list[dict]:
    """Load chunks either from an existing SQLite DB or directly from the MinerU chunk run.

    Use `load_chunks(["10.1038/..."], library_root=...)` for the Step 1 handoff API.
    Use `load_chunks("path/to/literature.db", "doc_0001")` for the legacy SQLite path.
    """
    if isinstance(source, list):
        if doc_id is not None:
            raise ValueError("doc_id is not used when source is a list of doc_ids_or_dois")
        return _load_chunks_from_library(source, library_root)
    return _load_chunks_from_db(source, doc_id)


def build_step1_output(library_dir: str, out_dir: str, min_core_count: int = 30) -> dict:
    stats = build_literature_db(library_dir, out_dir)
    db_path = Path(stats["db_path"])
    core = select_core_papers(str(db_path), anchors=[], min_count=min_core_count)
    facts: list[dict] = []
    for paper in core:
        chunks = load_chunks(db_path, paper.doc_id)
        paper_facts = extract_paper_facts(paper.doc_id, chunks, doi=paper.doi)
        facts.append(paper_facts.model_dump(mode="json"))

    output = {
        "db": stats,
        "core_papers": [paper.model_dump() for paper in core],
        "facts": facts,
    }
    out_path = Path(out_dir)
    (out_path / "core_papers.json").write_text(json.dumps(output["core_papers"], ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path / "facts.json").write_text(json.dumps(facts, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path / "step1_output.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def _group_chunks_by_doc(chunks: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for chunk in chunks:
        grouped.setdefault(chunk["doc_id"], []).append(chunk)
    return dict(sorted(grouped.items()))


def _core_paper_records(grouped_chunks: dict[str, list[dict]]) -> list[dict]:
    records: list[dict] = []
    for doc_id, chunks in grouped_chunks.items():
        first = chunks[0]
        records.append(
            {
                "doc_id": doc_id,
                "doi": first.get("doi"),
                "title": first.get("title"),
                "lib": first.get("lib"),
                "class_name": first.get("class_name"),
                "chunk_count": len(chunks),
            }
        )
    return records


def _render_d1_summary(core_papers: list[dict], paper_facts: list[PaperFacts]) -> str:
    by_doc = {item.doc_id: item for item in paper_facts}
    lines = [
        "# D1 Literature Extraction Summary",
        "",
        f"- core_papers: {len(core_papers)}",
        f"- paper_facts: {len(paper_facts)}",
        "",
        "| doc_id | DOI | chunks | structure | reaction | membrane | feed | performance | failure |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for paper in core_papers:
        facts = by_doc.get(paper["doc_id"])
        if facts is None:
            counts = [0, 0, 0, 0, 0, 0]
        else:
            counts = [
                len(facts.structure),
                len(facts.reaction),
                len(facts.membrane),
                len(facts.feed),
                len(facts.performance),
                len(facts.failure),
            ]
        lines.append(
            "| {doc_id} | {doi} | {chunks} | {counts} |".format(
                doc_id=paper["doc_id"],
                doi=paper.get("doi") or "",
                chunks=paper["chunk_count"],
                counts=" | ".join(str(count) for count in counts),
            )
        )
    lines.append("")
    return "\n".join(lines)


def select_by_libs_classes(
    libs: list[str],
    classes: list[str],
    library_root: str | Path | None = None,
) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    for lib in libs:
        for doi in select_by_group(lib, classes, library_root=library_root):
            if doi not in seen:
                selected.append(doi)
                seen.add(doi)
    return selected


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.replace(path)


def _read_existing_paper_fact(path: Path) -> PaperFacts:
    return PaperFacts.model_validate(json.loads(path.read_text(encoding="utf-8")))


def _extract_doc_with_retry(
    doc_id: str,
    doc_chunks: list[dict],
    paper_dir: Path,
    max_retries: int,
    retry_sleep_s: float,
    overwrite: bool,
) -> dict:
    out_file = paper_dir / f"{doc_id}.json"
    if out_file.exists() and not overwrite:
        existing = _read_existing_paper_fact(out_file)
        return {"doc_id": doc_id, "status": "skipped", "paper_facts": existing}

    last_error = ""
    for attempt in range(1, max_retries + 2):
        try:
            result = extract_paper_facts(doc_id, doc_chunks)
            _write_json(out_file, result.model_dump(mode="json"))
            return {"doc_id": doc_id, "status": "ok", "paper_facts": result, "attempt": attempt}
        except Exception as exc:  # noqa: BLE001 - batch runner must capture per-document failures.
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt > max_retries:
                return {
                    "doc_id": doc_id,
                    "status": "failed",
                    "error": last_error,
                    "traceback": traceback.format_exc(),
                    "attempt": attempt,
                }
            time.sleep(retry_sleep_s * attempt)
    raise RuntimeError("unreachable retry state")


def _write_batch_outputs(out_path: Path, core_papers: list[dict], paper_facts: list[PaperFacts], failures: list[dict]) -> dict:
    facts_json = [item.model_dump(mode="json") for item in sorted(paper_facts, key=lambda fact: fact.doc_id)]
    _write_json(out_path / "paper_facts.json", facts_json)
    _write_json(out_path / "failures.json", failures)
    (out_path / "D1_summary.md").write_text(_render_d1_summary(core_papers, paper_facts), encoding="utf-8")
    output = {
        "core_papers": core_papers,
        "paper_facts": facts_json,
        "failures": failures,
        "output_dir": str(out_path),
    }
    _write_json(out_path / "step1_output.json", output)
    return output


def _paper_text_blob(core_row: dict, facts_row: dict | None = None) -> str:
    parts = [
        str(core_row.get("title") or ""),
        str(core_row.get("doi") or ""),
        str(core_row.get("lib") or ""),
        str(core_row.get("class_name") or ""),
    ]
    if facts_row:
        for field in ("structure", "reaction", "membrane", "feed", "performance", "failure"):
            parts.extend(fact.get("value", "") for fact in facts_row.get(field, []))
    return " ".join(parts).lower()


def filter_reactor_core(
    batch_out_dir: str | Path,
    out_dir: str | Path,
    min_score: int = 2,
) -> dict:
    batch_path = Path(batch_out_dir)
    core_rows = json.loads((batch_path / "core_papers.json").read_text(encoding="utf-8"))
    facts_rows = json.loads((batch_path / "paper_facts.json").read_text(encoding="utf-8"))
    facts_by_doc = {row["doc_id"]: row for row in facts_rows}

    kept: list[dict] = []
    dropped: list[dict] = []
    for row in core_rows:
        blob = _paper_text_blob(row, facts_by_doc.get(row["doc_id"]))
        keep_hits = sum(1 for keyword in REACTOR_KEEP_KEYWORDS if keyword in blob)
        drop_hits = sum(1 for keyword in REACTOR_DROP_KEYWORDS if keyword in blob)
        score = keep_hits - (drop_hits * 2)
        record = {
            "doc_id": row["doc_id"],
            "doi": row.get("doi"),
            "title": row.get("title"),
            "lib": row.get("lib"),
            "class_name": row.get("class_name"),
            "chunk_count": row.get("chunk_count"),
            "keep_hits": keep_hits,
            "drop_hits": drop_hits,
            "score": score,
        }
        if score >= min_score:
            kept.append(record)
        else:
            dropped.append(record)

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    _write_json(out_path / "reactor_core_kept.json", kept)
    _write_json(out_path / "reactor_core_dropped.json", dropped)
    report = {
        "source_dir": str(batch_path),
        "kept_count": len(kept),
        "dropped_count": len(dropped),
        "min_score": min_score,
        "kept": kept,
        "dropped": dropped,
    }
    _write_json(out_path / "reactor_core_filter_report.json", report)
    return report


def run_step1_batch_extraction(
    library_root: str | Path,
    out_dir: str | Path,
    libs: list[str] | None = None,
    classes: list[str] | None = None,
    concurrency: int = 8,
    max_retries: int = 2,
    retry_sleep_s: float = 3.0,
    join_only: bool = False,
    overwrite: bool = False,
    limit: int | None = None,
) -> dict:
    if concurrency < 1:
        raise ValueError("concurrency must be >= 1")
    if max_retries < 0:
        raise ValueError("max_retries must be >= 0")

    root = Path(library_root)
    selected_libs = libs or DEFAULT_BATCH_LIBS
    selected_classes = classes or DEFAULT_BATCH_CLASSES
    dois = select_by_libs_classes(selected_libs, selected_classes, library_root=root)
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        dois = dois[:limit]

    _, chunk_run = _resolve_roots(root)
    lookup = _doc_lookup(root, chunk_run)
    available_dois = {str(meta["doi"]) for meta in lookup.values() if meta.get("doi")}
    requested_dois = list(dois)
    missing_dois = [doi for doi in requested_dois if doi not in available_dois]
    dois = [doi for doi in requested_dois if doi in available_dois]
    if not dois:
        raise ValueError("none of the selected DOI values are available in the parsed chunk corpus")

    chunks = load_chunks(dois, library_root=root)
    grouped = _group_chunks_by_doc(chunks)
    core_papers = _core_paper_records(grouped)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    join_manifest = {
        "library_root": str(root),
        "libs": selected_libs,
        "classes": selected_classes,
        "requested_doi_count": len(requested_dois),
        "available_doi_count": len(dois),
        "missing_doi_count": len(missing_dois),
        "missing_dois": missing_dois,
        "core_papers": core_papers,
        "chunk_count": len(chunks),
        "concurrency": concurrency,
        "max_retries": max_retries,
    }
    _write_json(out_path / "chunk_join_manifest.json", join_manifest)
    _write_json(out_path / "core_papers.json", core_papers)

    if join_only:
        output = {
            "core_papers": core_papers,
            "paper_facts": [],
            "failures": [],
            "output_dir": str(out_path),
            "join_only": True,
        }
        _write_json(out_path / "step1_output.json", output)
        return output

    paper_dir = out_path / "paper_facts_by_doc"
    paper_dir.mkdir(parents=True, exist_ok=True)
    failures: list[dict] = []
    paper_facts: list[PaperFacts] = []
    completed = 0
    total = len(grouped)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(
                _extract_doc_with_retry,
                doc_id,
                doc_chunks,
                paper_dir,
                max_retries,
                retry_sleep_s,
                overwrite,
            ): doc_id
            for doc_id, doc_chunks in grouped.items()
        }
        for future in as_completed(futures):
            completed += 1
            result = future.result()
            status = result["status"]
            if status in {"ok", "skipped"}:
                paper_facts.append(result["paper_facts"])
            else:
                failures.append({k: v for k, v in result.items() if k != "paper_facts"})
            if completed == total or completed % 10 == 0:
                checkpoint = {
                    "completed": completed,
                    "total": total,
                    "success_or_skipped": len(paper_facts),
                    "failed": len(failures),
                    "last_doc_id": result["doc_id"],
                }
                _write_json(out_path / "progress.json", checkpoint)
                _write_batch_outputs(out_path, core_papers, paper_facts, failures)

    return _write_batch_outputs(out_path, core_papers, paper_facts, failures)


def run_step1_extraction(doc_ids_or_dois: list[str], library_root: str | Path, out_dir: str | Path, join_only: bool = False) -> dict:
    chunks = load_chunks(doc_ids_or_dois, library_root=library_root)
    grouped = _group_chunks_by_doc(chunks)
    core_papers = _core_paper_records(grouped)

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    join_manifest = {
        "library_root": str(Path(library_root)),
        "requested": doc_ids_or_dois,
        "core_papers": core_papers,
        "chunk_count": len(chunks),
    }
    (out_path / "chunk_join_manifest.json").write_text(
        json.dumps(join_manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_path / "core_papers.json").write_text(json.dumps(core_papers, ensure_ascii=False, indent=2), encoding="utf-8")

    if join_only:
        output = {
            "core_papers": core_papers,
            "paper_facts": [],
            "output_dir": str(out_path),
            "join_only": True,
        }
        (out_path / "step1_output.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        return output

    paper_facts: list[PaperFacts] = []
    for doc_id, doc_chunks in grouped.items():
        paper_facts.append(extract_paper_facts(doc_id, doc_chunks))

    facts_json = [item.model_dump(mode="json") for item in paper_facts]
    (out_path / "paper_facts.json").write_text(json.dumps(facts_json, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_path / "D1_summary.md").write_text(_render_d1_summary(core_papers, paper_facts), encoding="utf-8")
    output = {
        "core_papers": core_papers,
        "paper_facts": facts_json,
        "output_dir": str(out_path),
    }
    (out_path / "step1_output.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Build Reactor Step 1 literature outputs.")
    parser.add_argument("--library-dir", help="MinerU literature directory containing parsed JSON and manifests.")
    parser.add_argument("--chunk-file", help="Pre-split chunk CSV, JSON, or JSONL using the project chunk schema.")
    parser.add_argument("--extract-chunk-file", help="Run Step 1 fact extraction over every doc_id in a pre-split body chunk file.")
    parser.add_argument("--step1-anchors", action="store_true", help="Run Step 1 extraction on the 8 anchor papers.")
    parser.add_argument("--batch-core", action="store_true", help="Run batch extraction for selected libs/classes in the full library.")
    parser.add_argument("--batch-libs", default=",".join(DEFAULT_BATCH_LIBS), help="Comma-separated libs for --batch-core.")
    parser.add_argument("--batch-classes", default=",".join(DEFAULT_BATCH_CLASSES), help="Comma-separated classes for --batch-core.")
    parser.add_argument("--doi", action="append", default=[], help="DOI to extract. Repeat for multiple papers.")
    parser.add_argument("--join-only", action="store_true", help="Validate DOI/doc/chunk joins without calling the LLM.")
    parser.add_argument("--concurrency", type=int, default=8, help="Concurrent papers for --batch-core.")
    parser.add_argument("--max-retries", type=int, default=2, help="Per-paper retry count for --batch-core.")
    parser.add_argument("--retry-sleep-s", type=float, default=3.0, help="Base sleep seconds between retries.")
    parser.add_argument("--overwrite", action="store_true", help="Re-extract papers even when per-doc output already exists.")
    parser.add_argument("--limit", type=int, help="Limit selected DOI count for smoke tests.")
    parser.add_argument("--out-dir", required=True, help="Output directory for D1 files.")
    parser.add_argument("--min-core-count", type=int, default=30, help="Minimum number of core papers to select.")
    args = parser.parse_args()

    direct_extract = args.step1_anchors or bool(args.doi)
    modes = sum(1 for flag in (bool(args.library_dir), bool(args.chunk_file), bool(args.extract_chunk_file), direct_extract, args.batch_core) if flag)
    if modes != 1:
        raise SystemExit("Pass exactly one mode: --library-dir, --chunk-file, --extract-chunk-file, --step1-anchors/--doi, or --batch-core.")
    if args.batch_core:
        libs = [item.strip() for item in args.batch_libs.split(",") if item.strip()]
        classes = [item.strip() for item in args.batch_classes.split(",") if item.strip()]
        output = run_step1_batch_extraction(
            _default_library_root(),
            args.out_dir,
            libs=libs,
            classes=classes,
            concurrency=args.concurrency,
            max_retries=args.max_retries,
            retry_sleep_s=args.retry_sleep_s,
            join_only=args.join_only,
            overwrite=args.overwrite,
            limit=args.limit,
        )
        print(
            json.dumps(
                {
                    "output_dir": output["output_dir"],
                    "n_papers": len(output["core_papers"]),
                    "n_facts": len(output["paper_facts"]),
                    "n_failures": len(output.get("failures", [])),
                    "join_only": output.get("join_only", False),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    if direct_extract:
        root = DEFAULT_CORE_ROOT if args.step1_anchors else _default_library_root()
        dois = DEFAULT_ANCHOR_DOIS if args.step1_anchors else args.doi
        output = run_step1_extraction(dois, root, args.out_dir, join_only=args.join_only)
        print(
            json.dumps(
                {"output_dir": output["output_dir"], "n_papers": len(output["core_papers"]), "join_only": output.get("join_only", False)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    if args.chunk_file:
        stats = build_literature_db_from_chunks(args.chunk_file, args.out_dir)
        print(json.dumps(stats, ensure_ascii=False, indent=2))
    elif args.extract_chunk_file:
        output = run_step1_chunk_file_extraction(
            args.extract_chunk_file,
            args.out_dir,
            concurrency=args.concurrency,
            max_retries=args.max_retries,
            retry_sleep_s=args.retry_sleep_s,
            join_only=args.join_only,
            overwrite=args.overwrite,
            limit=args.limit,
        )
        print(
            json.dumps(
                {
                    "output_dir": output["output_dir"],
                    "n_papers": len(output["core_papers"]),
                    "n_facts": len(output["paper_facts"]),
                    "n_failures": len(output.get("failures", [])),
                    "join_only": output.get("join_only", False),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        output = build_step1_output(args.library_dir, args.out_dir, args.min_core_count)
        print(json.dumps(output["db"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
