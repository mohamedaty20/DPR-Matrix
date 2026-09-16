"""Per-user session state, backed by app.storage.user."""
from __future__ import annotations

import threading
import uuid

from nicegui import app

from core.models import ExtractedDocument, AggregatedReport

_KEY = "dpr_matrix"

# ---------------------------------------------------------------------------
# In-process byte registry.
#
# app.storage.user is JSON-serialised, so raw bytes cannot live there.
# Single-worker NiceGUI → a module-level dict is safe and never pickled.
# Bytes are freed on remove_queued() / clear_queue().
# ---------------------------------------------------------------------------
_FILE_BYTES: dict[str, bytes] = {}

# ---------------------------------------------------------------------------
# Cooperative cancel flag for the current aggregation job.
#
# NOTE: this is process-global, not per-session. That matches the current
# single-worker, effectively single-user deployment. If DPR-Matrix ever
# becomes multi-tenant, move this into a per-session dict keyed on
# app.storage.browser["id"].
# ---------------------------------------------------------------------------
_CANCEL = threading.Event()

# ---------------------------------------------------------------------------
# Thread-safe event queue.
#
# aggregate() runs in a worker thread (run.io_bound). It must not touch
# NiceGUI storage directly. It pushes events here; a UI timer drains them
# on the event loop and updates the log + file badges.
# ---------------------------------------------------------------------------
_EVENTS: list[tuple[str, dict]] = []
_EVENTS_LOCK = threading.Lock()


def _bucket() -> dict:
    store = app.storage.user
    if _KEY not in store:
        store[_KEY] = {
            "docs": [],
            "report": None,
            "report_id": None,
            "logs": [],
            "queue": [],
        }
    store[_KEY].setdefault("queue", [])
    return store[_KEY]


# ── Docs (kept for export / history compatibility) ────────────────────────
def add_doc(doc: ExtractedDocument) -> None:
    _bucket()["docs"].append(doc)

def docs() -> list[ExtractedDocument]:
    return _bucket()["docs"]

def set_docs(docs_list: list[ExtractedDocument]) -> None:
    _bucket()["docs"] = list(docs_list)


# ── Report ────────────────────────────────────────────────────────────────
def set_report(r: AggregatedReport | None) -> None:
    _bucket()["report"] = r

def report() -> AggregatedReport | None:
    return _bucket()["report"]

def set_report_id(rid: int | None) -> None:
    _bucket()["report_id"] = rid

def report_id() -> int | None:
    return _bucket()["report_id"]


# ── Logs ──────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    logs = _bucket()["logs"]
    logs.append(str(msg))
    if len(logs) > 500:
        del logs[:250]

def logs() -> list[str]:
    return _bucket()["logs"]


# ── File Queue ────────────────────────────────────────────────────────────
def queue_files() -> list[dict]:
    return _bucket()["queue"]

def enqueue(name: str, data: bytes, mime: str = "") -> str:
    token = uuid.uuid4().hex
    _FILE_BYTES[token] = data
    _bucket()["queue"].append({
        "token":  token,
        "name":   name,
        "size":   len(data),
        "mime":   mime,
        "status": "queued",   # queued | extracting | done | error
        "error":  "",
    })
    return token

def remove_queued(token: str) -> None:
    q = _bucket()["queue"]
    _bucket()["queue"] = [f for f in q if f["token"] != token]
    _FILE_BYTES.pop(token, None)

def clear_queue() -> None:
    for f in _bucket()["queue"]:
        _FILE_BYTES.pop(f["token"], None)
    _bucket()["queue"] = []

def get_bytes(token: str) -> bytes | None:
    return _FILE_BYTES.get(token)

def set_status(token: str, status: str, error: str = "") -> None:
    for f in _bucket()["queue"]:
        if f["token"] == token:
            f["status"] = status
            f["error"] = error
            return


# ── Cancel flag ───────────────────────────────────────────────────────────
def request_cancel() -> None:
    _CANCEL.set()

def is_cancelled() -> bool:
    return _CANCEL.is_set()

def clear_cancel() -> None:
    _CANCEL.clear()


# ── Event queue (called from worker threads) ──────────────────────────────
def push_event(kind: str, **payload) -> None:
    with _EVENTS_LOCK:
        _EVENTS.append((kind, payload))

def drain_events() -> list[tuple[str, dict]]:
    with _EVENTS_LOCK:
        out = list(_EVENTS)
        _EVENTS.clear()
    return out

def clear_events() -> None:
    with _EVENTS_LOCK:
        _EVENTS.clear()


# ── Reset ─────────────────────────────────────────────────────────────────
def reset() -> None:
    """Clear docs / report / logs / events. Does NOT touch the file queue."""
    _bucket().update({
        "docs": [], "report": None, "report_id": None, "logs": [],
    })
    clear_events()
