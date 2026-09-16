"""Turso (libSQL) persistence layer for DPR-Matrix."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any

import libsql

from config import settings
from core.models import AggregatedReport


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS reports (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at    TEXT NOT NULL,
        project_name  TEXT,
        report_date   TEXT,
        site_location TEXT,
        prepared_by   TEXT,
        source_files  TEXT,
        payload       TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS uploads (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        report_id       INTEGER REFERENCES reports(id) ON DELETE CASCADE,
        filename        TEXT,
        mime            TEXT,
        bytes           INTEGER,
        extracted_chars INTEGER,
        created_at      TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_uploads_report  ON uploads(report_id)",
]


# ---------------------------------------------------------------------------
# Migrations — idempotent column additions for older live databases.
# `CREATE TABLE IF NOT EXISTS` never alters an existing table, so any column
# that shipped after the very first release must be added explicitly here.
# ---------------------------------------------------------------------------
_MIGRATIONS: list[tuple[str, str, str]] = [
    ("reports", "project_name",  "TEXT"),
    ("reports", "report_date",   "TEXT"),
    ("reports", "site_location", "TEXT"),
    ("reports", "prepared_by",   "TEXT"),
    ("reports", "source_files",  "TEXT"),
]


def get_db():
    return libsql.connect(
        database=settings.TURSO_URL,
        auth_token=settings.TURSO_TOKEN,
    )


def _column_exists(conn, table: str, column: str) -> bool:
    try:
        cur = conn.execute(f"PRAGMA table_info({table})")
        return any(row[1] == column for row in cur.fetchall())
    except Exception:
        return False


def _apply_migrations(conn) -> None:
    for table, column, coltype in _MIGRATIONS:
        try:
            if _column_exists(conn, table, column):
                continue
            conn.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"
            )
            conn.commit()
            print(f"[db] migration: added {table}.{column}", flush=True)
        except Exception as e:
            print(
                f"[db] migration skipped {table}.{column}: "
                f"{type(e).__name__}: {e}",
                flush=True,
            )


def init_db() -> None:
    conn = get_db()
    for stmt in _SCHEMA:
        conn.execute(stmt)
    conn.commit()
    _apply_migrations(conn)
    print("[db] schema ready")


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------
def save_report(report: AggregatedReport,
                uploads_meta: list[dict] | None = None) -> int:
    """Persist one aggregated report. Returns the new report id."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    payload = json.dumps(report.to_dict(), ensure_ascii=False)

    cur = conn.execute(
        """
        INSERT INTO reports
            (created_at, project_name, report_date, site_location,
             prepared_by, source_files, payload)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            now,
            report.project_name or "",
            report.report_date or "",
            report.site_location or "",
            report.prepared_by or "",
            ", ".join(report.source_files or []),
            payload,
        ),
    )
    conn.commit()
    report_id = cur.lastrowid

    if uploads_meta:
        for u in uploads_meta:
            conn.execute(
                """
                INSERT INTO uploads
                    (report_id, filename, mime, bytes, extracted_chars, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    report_id,
                    u.get("filename", ""),
                    u.get("mime", ""),
                    int(u.get("bytes", 0)),
                    int(u.get("extracted_chars", 0)),
                    now,
                ),
            )
        conn.commit()

    return report_id


def delete_report(report_id: int) -> None:
    conn = get_db()
    conn.execute("DELETE FROM uploads WHERE report_id = ?", (report_id,))
    conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    conn.commit()


def cleanup_old_reports(keep_per_project: int = 90) -> int:
    """Keep the newest N reports per project. Returns rows deleted."""
    conn = get_db()
    cur = conn.execute(
        """
        DELETE FROM reports
        WHERE id NOT IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY project_name
                           ORDER BY created_at DESC
                       ) AS rn
                FROM reports
            )
            WHERE rn <= ?
        )
        """,
        (keep_per_project,),
    )
    conn.commit()
    return cur.rowcount or 0


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------
def list_reports(limit: int = 100) -> list[dict[str, Any]]:
    """
    Return recent report summaries. Tries the full column set first; if the
    live table is missing an optional column, falls back to a minimal query
    so History and risk analysis keep working.
    """
    conn = get_db()
    try:
        cur = conn.execute(
            """
            SELECT id, created_at, project_name, report_date,
                   site_location, prepared_by, source_files
            FROM reports
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
    except Exception as e:
        print(f"[db] list_reports fallback ({type(e).__name__}): {e}", flush=True)
        cur = conn.execute(
            """
            SELECT id, created_at,
                   '' AS project_name,
                   '' AS report_date,
                   '' AS site_location,
                   '' AS prepared_by,
                   '' AS source_files
            FROM reports
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def get_report(report_id: int) -> AggregatedReport | None:
    conn = get_db()
    cur = conn.execute(
        "SELECT payload FROM reports WHERE id = ?", (report_id,)
    )
    row = cur.fetchone()
    if not row:
        return None
    data = json.loads(row[0])
    return AggregatedReport(**{
        k: v for k, v in data.items()
        if k in AggregatedReport.__dataclass_fields__
    })


def count_reports() -> int:
    conn = get_db()
    cur = conn.execute("SELECT COUNT(*) FROM reports")
    row = cur.fetchone()
    return int(row[0]) if row else 0
