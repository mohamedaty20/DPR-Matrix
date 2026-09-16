"""Per-client session state. Isolated per browser tab. GC-friendly."""
from __future__ import annotations
from nicegui import app
from core.models import ExtractedDocument, AggregatedReport

_KEY = "dpr_matrix"

def _bucket() -> dict:
    store = app.storage.client
    if _KEY not in store:
        store[_KEY] = {"docs": [], "report": None, "logs": []}
    return store[_KEY]

# --- Docs ---
def add_doc(doc: ExtractedDocument) -> None: _bucket()["docs"].append(doc)
def docs() -> list[ExtractedDocument]: return _bucket()["docs"]

# --- Report ---
def set_report(r: AggregatedReport | None) -> None: _bucket()["report"] = r
def report() -> AggregatedReport | None: return _bucket()["report"]

# --- Logs ---
def log(msg: str) -> None:
    logs = _bucket()["logs"]
    logs.append(msg)
    if len(logs) > 500:
        del logs[:250]  # trim to bound memory
def logs() -> list[str]: return _bucket()["logs"]

# --- Reset ---
def reset() -> None:
    _bucket().update({"docs": [], "report": None, "logs": []})
