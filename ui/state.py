"""Per-user session state, backed by app.storage.user."""
from __future__ import annotations

import threading
import uuid
from datetime import datetime

from nicegui import app

from core.models import ExtractedDocument, AggregatedReport

_KEY = "dpr_matrix"

_FILE_BYTES: dict[str, bytes] = {}
_CANCEL = threading.Event()
_EVENTS: list[tuple[str, dict]] = []
_EVENTS_LOCK = threading.Lock()


def _bucket() -> dict:
    store = app.storage.user
    if _KEY not in store:
        store[_KEY] = {
            "docs": [], "report": None, "report_id": None,
            "logs": [], "queue": [], "zones": {},
        }
    store[_KEY].setdefault("queue", [])
    store[_KEY].setdefault("zones", {})
    return store[_KEY]


# ── Docs ──────────────────────────────────────────────────────────────────
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


# ── File queue ────────────────────────────────────────────────────────────
def queue_files() -> list[dict]:
    return _bucket()["queue"]

def enqueue(name: str, data: bytes, mime: str = "") -> str:
    token = uuid.uuid4().hex
    _FILE_BYTES[token] = data
    _bucket()["queue"].append({
        "token": token, "name": name, "size": len(data),
        "mime": mime, "status": "queued", "error": "",
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


# ── Cancel ────────────────────────────────────────────────────────────────
def request_cancel() -> None:
    _CANCEL.set()

def is_cancelled() -> bool:
    return _CANCEL.is_set()

def clear_cancel() -> None:
    _CANCEL.clear()


# ── Event queue ───────────────────────────────────────────────────────────
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


# ── Zone registry ─────────────────────────────────────────────────────────
def zones() -> dict[str, dict]:
    return _bucket()["zones"]

def set_zone_stage(zone_id: str, stage: str, note: str = "") -> None:
    z = zones()
    entry = z.get(zone_id) or {"stage": "not_started", "note": "", "updated": ""}
    entry["stage"] = stage
    if note:
        entry["note"] = note
    entry["updated"] = datetime.now().isoformat(timespec="seconds")
    z[zone_id] = entry

def ensure_zones(zone_ids: list[str]) -> None:
    z = zones()
    for zid in zone_ids:
        if zid and zid not in z:
            z[zid] = {"stage": "not_started", "note": "", "updated": ""}

def reset_zones() -> None:
    _bucket()["zones"] = {}


# ── Reset ─────────────────────────────────────────────────────────────────
def reset() -> None:
    """Clear docs / report / logs / events. Keeps queue and zones."""
    _bucket().update({
        "docs": [], "report": None, "report_id": None, "logs": [],
    })
    clear_events()

# ── S-curve targets ───────────────────────────────────────────────────────
def s_curve_targets() -> dict[str, dict]:
    """{activity: {"target": float, "start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}}"""
    b = _bucket()
    b.setdefault("s_curve_targets", {})
    return b["s_curve_targets"]


def set_s_curve_target(activity: str, target: float, start: str, end: str) -> None:
    s_curve_targets()[activity] = {
        "target": float(target), "start": start, "end": end,
    }


def clear_s_curve_targets() -> None:
    _bucket()["s_curve_targets"] = {}


# ── Risk forecast cache ───────────────────────────────────────────────────
def risk_cache() -> dict:
    b = _bucket()
    b.setdefault("risk_cache", {})
    return b["risk_cache"]


def set_risk_cache(key: str, value: dict) -> None:
    risk_cache()[key] = value


def clear_risk_cache() -> None:
    _bucket()["risk_cache"] = {}
