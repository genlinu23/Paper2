from __future__ import annotations

import sqlite3
from pathlib import Path

from .contracts import LiteratureSource


def search(query: str, top_k: int = 20, db_path: str | Path | None = None) -> list[LiteratureSource]:
    if not db_path:
        raise ValueError("db_path is required for search")
    path = Path(db_path)
    if path.is_dir():
        path = path / "literature.db"
    if not path.exists():
        raise FileNotFoundError(f"literature database not found: {path}")

    terms = [t.lower() for t in query.split() if t.strip()]
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        """
        SELECT
            p.doc_id,
            p.doi,
            p.title,
            p.summary_json,
            COALESCE(group_concat(c.text, ' '), '') AS chunk_text
        FROM paper_summary p
        LEFT JOIN chunks c ON c.doc_id = p.doc_id
        GROUP BY p.doc_id, p.doi, p.title, p.summary_json
        """
    ).fetchall()
    scored: list[tuple[int, LiteratureSource]] = []
    for row in rows:
        blob = (
            f"{row['doc_id']} {row['doi'] or ''} {row['title'] or ''} "
            f"{row['summary_json'] or ''} {row['chunk_text'] or ''}"
        ).lower()
        score = sum(blob.count(term) for term in terms) if terms else 0
        if score > 0 or not terms:
            scored.append((score, LiteratureSource(doc_id=row["doc_id"], doi=row["doi"], title=row["title"])))
    scored.sort(key=lambda item: (-item[0], item[1].doc_id))
    return [item[1] for item in scored[:top_k]]


def get_anchor_papers(db_path: str | Path) -> list[LiteratureSource]:
    path = Path(db_path)
    if path.is_dir():
        path = path / "literature.db"
    if not path.exists():
        raise FileNotFoundError(f"literature database not found: {path}")
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT doc_id, doi, title FROM paper_summary WHERE anchor = 1 ORDER BY score DESC, doc_id"
    ).fetchall()
    return [LiteratureSource(doc_id=row["doc_id"], doi=row["doi"], title=row["title"]) for row in rows]
