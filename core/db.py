import libsql
from config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    project_name TEXT,
    report_date TEXT,
    source_files TEXT,
    payload TEXT
);
CREATE TABLE IF NOT EXISTS uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER,
    filename TEXT,
    mime TEXT,
    bytes INTEGER,
    extracted_chars INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

def get_db():
    return libsql.connect(
        database=settings.TURSO_URL,
        auth_token=settings.TURSO_TOKEN,
    )

def init_db() -> None:
    conn = get_db()
    for stmt in _SCHEMA.strip().split(";"):
        s = stmt.strip()
        if s:
            conn.execute(s)
    conn.commit()
    print("[db] schema ready")

def save_report(project_name: str, report_date: str,
                source_files: str, payload_json: str) -> int:
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO reports (project_name, report_date, source_files, payload) "
        "VALUES (?, ?, ?, ?)",
        (project_name, report_date, source_files, payload_json),
    )
    conn.commit()
    return cur.lastrowid
