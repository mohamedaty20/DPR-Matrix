"""Two-pass aggregator.

Pass 1 — Gemini extracts EACH file independently into a strict schema.
Pass 2 — Python merges deterministically: normalize → group → sum.

The LLM never does the merge. All cross-file logic is auditable Python.

Pass 6 adds:
  * on_event(kind, **payload) — emitted from the worker thread; the UI
    drains these via state.drain_events() and renders them.
  * should_cancel() — cooperative cancellation checked between files
    and before Pass 2.
  * max_seconds — wall-clock watchdog. Whichever of cancel / watchdog
    trips first wins; both return None so the caller can distinguish
    "aborted" from "empty".
"""
from __future__ import annotations

import json
import re
import time
from typing import Callable

from core.models import ExtractedDocument, AggregatedReport
from core.gemini_client import generate_text
from core.errors import GeminiError
from core.normalize import (
    norm_building, norm_floor, norm_activity, norm_unit,
    to_float, fmt_num,
)


# ═══════════════════════════════════════════════════════════════════════════
# THE PROMPT — DO NOT CHANGE
# ═══════════════════════════════════════════════════════════════════════════
_SYSTEM = r"""You extract a Daily Progress Report (DPR) from ONE source document.
It may be a scan, a photo, an Excel export, or raw text.
Return STRICT JSON — no prose, no markdown fences.

═══════════════════════════════════════════════════════════════════════
CRITICAL RULES
═══════════════════════════════════════════════════════════════════════

RULE 1 — Location and activity are always SEPARATE fields.
   GOOD: {"building":"70","floor":"4","activity":"Mortar works"}
   BAD:  {"label":"Building No 70, Floor No 4 + 1 helper - Mortar works"}

RULE 2 — Helper counts go ONLY in the "helpers" field. NEVER in floor, zone, activity, quantity, or notes.
   Source: "Floor 4 + 1 helper"
   ✓ building="70", floor="4", helpers=1
   ✗ floor="4 + 1 helper"
   ✗ notes="Floor listed as 4 + 1 helper"

RULE 3 — Workforce goes in "skilled" and "helpers" ONLY. NEVER in "quantity".
   "10 workers + 3 helpers" → skilled=10, helpers=3, quantity="", unit=""
   "13 masons + 2 helpers"  → skilled=13, helpers=2, quantity="", unit=""
   "5 workers"              → skilled=5,  helpers=0, quantity="", unit=""
   "4"                      → skilled=4,  helpers=0, quantity="", unit=""

RULE 4 — "quantity" is a WORK or MATERIAL measurement, never a headcount.
   Only fill quantity when the source gives a measurable amount of work or material:
   "15 m²"      → quantity=15,  unit="m2"
   "3 m³"       → quantity=3,   unit="m3"
   "200 bags"   → quantity=200, unit="bags"
   If a row has BOTH crew and work quantity, fill both.
   If no work quantity is given, leave quantity="" and unit="".

RULE 5 — Building and floor are always separate.
   "Building No 53, Floor No 2" → building="53", floor="2"
   "Bldg 59 - 3rd floor"        → building="59", floor="3"
   "B-87 F3"                    → building="87", floor="3"

RULE 6 — Normalize activity to this controlled vocabulary when it matches:
   Mortar works · Brickworks · Sealer works · Plastering · Painting
   Tiling · Steel fixing · Concrete works · Formwork · Carpentry
   Electrical · Plumbing · Excavation · Backfilling · Waterproofing
   Gypsum works · Ceiling works

RULE 7 — One row per (building, floor, activity). Duplicate combinations
   within the same source → sum the quantities and crews.

RULE 8 — "notes" field is ONLY for site remarks the source explicitly
   contains (e.g. "delay due to rain", "waiting for material").
   Do NOT put your own observations in notes. Do NOT describe how you
   parsed the data. Do NOT put helper info in notes. Leave it empty "".

RULE 9 — Never invent data. Missing field → empty string "" or 0.

═══════════════════════════════════════════════════════════════════════
OUTPUT SCHEMA — return ONLY this JSON object
═══════════════════════════════════════════════════════════════════════

{
  "project_name": "",
  "report_date":  "",
  "site_location": "",
  "prepared_by":  "",
  "weather":      "",
  "shift":        "",

  "work_progress": [
    {
      "building": "",
      "floor":    "",
      "zone":     "",
      "activity": "",
      "quantity": "",
      "unit":     "",
      "skilled":  "",
      "helpers":  "",
      "progress_pct": "",
      "notes":    ""
    }
  ],

  "equipment": [
    { "name":"", "model":"", "quantity":"", "status":"", "location":"", "notes":"" }
  ],

  "materials": [
    { "name":"", "grade":"", "quantity":"", "unit":"", "location":"", "notes":"" }
  ],

  "personnel": [
    { "trade":"", "count":"", "building":"", "notes":"" }
  ],

  "hse_observations": [],
  "quality_checks":   [],
  "issues_risks":     [],
  "next_day_plan":    [],
  "incidents":        ""
}"""


def _prompt_for(doc: ExtractedDocument) -> str:
    return (
        f"{_SYSTEM}\n\n"
        f"SOURCE FILENAME: {doc.filename}\n\n"
        f"DOCUMENT CONTENT:\n{doc.raw_text[:30000]}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# JSON extraction
# ═══════════════════════════════════════════════════════════════════════════
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _extract_json(raw: str) -> dict:
    if not raw:
        raise GeminiError("Gemini returned an empty response.")
    for attempt in (
        lambda: json.loads(raw),
        lambda: json.loads(_FENCE.search(raw).group(1)) if _FENCE.search(raw) else None,
        lambda: json.loads(raw[raw.find("{"):raw.rfind("}") + 1]),
    ):
        try:
            v = attempt()
            if isinstance(v, dict):
                return v
        except (json.JSONDecodeError, AttributeError, TypeError):
            continue
    raise GeminiError(f"Gemini returned non-JSON output ({len(raw)} chars).")


# ═══════════════════════════════════════════════════════════════════════════
# Noise filter for notes
# ═══════════════════════════════════════════════════════════════════════════
_NOTE_NOISE = re.compile(
    r"(floor\s+listed\s+as|helper[s]?\s+listed|crew\s+listed|"
    r"as\s+written\s+in|parsed\s+as|the\s+source\s+shows|"
    r"according\s+to\s+the\s+source|combined\s+from)",
    re.IGNORECASE,
)


def _clean_note(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    if _NOTE_NOISE.search(s):
        return ""
    return s


# ═══════════════════════════════════════════════════════════════════════════
# PASS 1 — per-file structured extraction
# ═══════════════════════════════════════════════════════════════════════════
def _extract_one(doc: ExtractedDocument) -> dict:
    print(f"[agg] extracting {doc.filename} ({len(doc.raw_text)} chars) …", flush=True)
    raw = generate_text(_prompt_for(doc), json_mode=True)
    print(f"[agg] {doc.filename} → {len(raw)} chars of JSON", flush=True)
    data = _extract_json(raw)

    fn = doc.filename
    for key in ("work_progress", "equipment", "materials", "personnel"):
        for row in data.get(key, []) or []:
            if isinstance(row, dict):
                row.setdefault("sources", [])
                if fn not in row["sources"]:
                    row["sources"].append(fn)
    return data


# ═══════════════════════════════════════════════════════════════════════════
# PASS 2 — deterministic merge
# ═══════════════════════════════════════════════════════════════════════════
def _merge_work(rows: list[dict]) -> list[dict]:
    """Group by (normalized building, floor, activity). Sum quantities & crews."""
    groups: dict[tuple[str, str, str], dict] = {}

    for r in rows:
        if not isinstance(r, dict):
            continue
        b = norm_building(r.get("building", ""))
        f = norm_floor(r.get("floor", ""))
        a = norm_activity(r.get("activity", ""))
        if a == "" and b == "?" and f == "?":
            continue
        key = (b, f, a)

        qty   = to_float(r.get("quantity"))
        sk    = to_float(r.get("skilled"))
        hp    = to_float(r.get("helpers"))
        unit  = norm_unit(r.get("unit", ""))
        note  = _clean_note(r.get("notes", ""))
        srcs  = r.get("sources") or []
        if isinstance(srcs, str):
            srcs = [srcs]

        if key not in groups:
            groups[key] = {
                "building": b,
                "floor":    f,
                "zone":     (r.get("zone") or "").strip(),
                "activity": a,
                "quantity": qty,   # may be None
                "unit":     unit,
                "skilled":  sk,    # may be None
                "helpers":  hp,    # may be None
                "progress_pct": (r.get("progress_pct") or "").strip(),
                "notes":    [note] if note else [],
                "sources":  list(dict.fromkeys(srcs)),
            }
        else:
            g = groups[key]
            if qty is not None:
                g["quantity"] = (g["quantity"] or 0) + qty
            if sk is not None:
                g["skilled"] = (g["skilled"] or 0) + sk
            if hp is not None:
                g["helpers"] = (g["helpers"] or 0) + hp
            if unit and not g["unit"]:
                g["unit"] = unit
            if note and note not in g["notes"]:
                g["notes"].append(note)
            for s in srcs:
                if s not in g["sources"]:
                    g["sources"].append(s)

    out = []
    for g in groups.values():
        sk = g["skilled"]
        hp = g["helpers"]
        if sk is not None or hp is not None:
            g["crew_total"] = fmt_num((sk or 0) + (hp or 0))
        else:
            g["crew_total"] = ""

        g["quantity"] = fmt_num(g["quantity"]) if g["quantity"] is not None else ""
        g["skilled"]  = fmt_num(sk) if sk is not None else ""
        g["helpers"]  = fmt_num(hp) if hp is not None else ""
        g["notes"]    = " | ".join(g["notes"])

        out.append({
            "building":     g["building"],
            "floor":        g["floor"],
            "zone":         g["zone"],
            "activity":     g["activity"],
            "quantity":     g["quantity"],
            "unit":         g["unit"],
            "skilled":      g["skilled"],
            "helpers":      g["helpers"],
            "crew_total":   g["crew_total"],
            "progress_pct": g["progress_pct"],
            "notes":        g["notes"],
            "sources":      g["sources"],
        })

    def sort_key(x):
        try: b = int(x["building"])
        except (ValueError, TypeError): b = 10**9
        try: f = int(x["floor"])
        except (ValueError, TypeError): f = 10**9
        return (b, f, x["activity"])
    out.sort(key=sort_key)
    return out


def _merge_equipment(rows: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        name = (r.get("name") or "").strip()
        model = (r.get("model") or "").strip()
        if not name and not model:
            continue
        key = f"{name.lower()}|{model.lower()}"
        srcs = r.get("sources") or []
        if isinstance(srcs, str):
            srcs = [srcs]
        qty = to_float(r.get("quantity"))
        note = _clean_note(r.get("notes", ""))
        if key not in groups:
            groups[key] = {
                "name": name, "model": model,
                "quantity": qty,
                "status": (r.get("status") or "").strip(),
                "location": (r.get("location") or "").strip(),
                "notes": [note] if note else [],
                "sources": list(dict.fromkeys(srcs)),
            }
        else:
            g = groups[key]
            if qty is not None:
                g["quantity"] = (g["quantity"] or 0) + qty
            if note and note not in g["notes"]:
                g["notes"].append(note)
            for s in srcs:
                if s not in g["sources"]:
                    g["sources"].append(s)
    out = []
    for g in groups.values():
        g["quantity"] = fmt_num(g["quantity"]) if g["quantity"] is not None else ""
        g["notes"] = " | ".join(g["notes"])
        out.append(g)
    return out


def _merge_materials(rows: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        name = (r.get("name") or "").strip()
        grade = (r.get("grade") or "").strip()
        if not name:
            continue
        key = f"{name.lower()}|{grade.lower()}"
        unit = norm_unit(r.get("unit", ""))
        qty = to_float(r.get("quantity"))
        note = _clean_note(r.get("notes", ""))
        srcs = r.get("sources") or []
        if isinstance(srcs, str):
            srcs = [srcs]
        if key not in groups:
            groups[key] = {
                "name": name, "grade": grade,
                "quantity": qty, "unit": unit,
                "location": (r.get("location") or "").strip(),
                "notes": [note] if note else [],
                "sources": list(dict.fromkeys(srcs)),
            }
        else:
            g = groups[key]
            if qty is not None and unit and g["unit"] == unit:
                g["quantity"] = (g["quantity"] or 0) + qty
            elif qty is not None and not g["quantity"]:
                g["quantity"] = qty
            if note and note not in g["notes"]:
                g["notes"].append(note)
            for s in srcs:
                if s not in g["sources"]:
                    g["sources"].append(s)
    out = []
    for g in groups.values():
        g["quantity"] = fmt_num(g["quantity"]) if g["quantity"] is not None else ""
        g["notes"] = " | ".join(g["notes"])
        out.append(g)
    return out


def _merge_personnel(rows: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        trade = (r.get("trade") or "").strip().title()
        if not trade:
            continue
        count = to_float(r.get("count"))
        note = _clean_note(r.get("notes", ""))
        srcs = r.get("sources") or []
        if isinstance(srcs, str):
            srcs = [srcs]
        if trade not in groups:
            groups[trade] = {
                "trade": trade,
                "count": count,
                "building": (r.get("building") or "").strip(),
                "notes": [note] if note else [],
                "sources": list(dict.fromkeys(srcs)),
            }
        else:
            g = groups[trade]
            if count is not None:
                g["count"] = (g["count"] or 0) + count
            if note and note not in g["notes"]:
                g["notes"].append(note)
            for s in srcs:
                if s not in g["sources"]:
                    g["sources"].append(s)
    out = []
    for g in groups.values():
        g["count"] = fmt_num(g["count"]) if g["count"] is not None else ""
        g["notes"] = " | ".join(g["notes"])
        out.append(g)
    out.sort(key=lambda x: x["trade"])
    return out


def _clean_strings(items: list) -> list[str]:
    seen, out = set(), []
    for it in items or []:
        s = _clean_note(str(it))
        if s and s.lower() not in seen:
            seen.add(s.lower()); out.append(s)
    return out


# ═══════════════════════════════════════════════════════════════════════════
# Public API — Pass 6 signature (backward compatible: all kwargs optional)
# ═══════════════════════════════════════════════════════════════════════════
def aggregate(
    docs: list[ExtractedDocument],
    *,
    on_event: Callable[..., None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    max_seconds: float | None = 600.0,
) -> AggregatedReport | None:
    """
    Two-pass aggregation.

    Returns the AggregatedReport on success, or None if the run was
    cancelled (by should_cancel) or tripped the wall-clock watchdog.

    Emitted events (via on_event):
      "file_start"  — filename, index, total
      "file_ok"     — filename, index, total
      "file_err"    — filename, index, total, error
      "merge_start" — num_files
      "done"        — report
      "cancelled"   — reason: "cancel" | "timeout", phase: "extract" | "merge"
    """
    def emit(kind: str, **payload) -> None:
        if on_event is None:
            return
        try:
            on_event(kind, **payload)
        except Exception as e:
            print(f"[agg] on_event({kind}) raised: {e}", flush=True)

    started = time.monotonic()

    def stop_reason() -> str:
        if should_cancel is not None and should_cancel():
            return "cancel"
        if max_seconds is not None and (time.monotonic() - started) > max_seconds:
            return "timeout"
        return ""

    print(f"[agg] starting aggregate with {len(docs)} doc(s)", flush=True)
    if not docs:
        raise GeminiError("No documents to aggregate.")

    total = len(docs)
    per_file: list[dict] = []

    # ---- Pass 1: per-file LLM extraction -------------------------------
    for i, d in enumerate(docs, start=1):
        reason = stop_reason()
        if reason:
            print(f"[agg] {reason} before file {i}/{total}", flush=True)
            emit("cancelled", reason=reason, phase="extract", index=i, total=total)
            return None

        emit("file_start", filename=d.filename, index=i, total=total)
        try:
            per_file.append(_extract_one(d))
            emit("file_ok", filename=d.filename, index=i, total=total)
        except Exception as e:
            print(f"[agg] FAILED {d.filename}: {type(e).__name__}: {e}", flush=True)
            per_file.append({"_error": f"{d.filename}: {type(e).__name__}: {e}"})
            emit("file_err", filename=d.filename, index=i, total=total,
                 error=f"{type(e).__name__}: {e}")

    reason = stop_reason()
    if reason:
        emit("cancelled", reason=reason, phase="merge")
        return None

    # ---- Pass 2: deterministic merge -----------------------------------
    emit("merge_start", num_files=total)

    work_rows, equip_rows, mat_rows, pers_rows = [], [], [], []
    hse, qc, risks, plan = [], [], [], []
    incidents_parts = []
    header: dict = {}

    for data in per_file:
        if "_error" in data:
            continue
        work_rows  += [r for r in (data.get("work_progress") or []) if isinstance(r, dict)]
        equip_rows += [r for r in (data.get("equipment")     or []) if isinstance(r, dict)]
        mat_rows   += [r for r in (data.get("materials")     or []) if isinstance(r, dict)]
        pers_rows  += [r for r in (data.get("personnel")     or []) if isinstance(r, dict)]
        hse   += data.get("hse_observations") or []
        qc    += data.get("quality_checks")   or []
        risks += data.get("issues_risks")     or []
        plan  += data.get("next_day_plan")    or []
        if data.get("incidents"):
            incidents_parts.append(str(data["incidents"]).strip())
        for k in ("project_name", "report_date", "site_location",
                  "prepared_by", "weather", "shift"):
            if not header.get(k) and data.get(k):
                header[k] = data[k]

    print(f"[agg] pass 1 done; merging {len(work_rows)} work rows …", flush=True)
    report = AggregatedReport(
        project_name  = header.get("project_name", ""),
        report_date   = header.get("report_date", ""),
        site_location = header.get("site_location", ""),
        prepared_by   = header.get("prepared_by", ""),
        weather       = header.get("weather", ""),
        shift         = header.get("shift", ""),
        work_progress = _merge_work(work_rows),
        equipment     = _merge_equipment(equip_rows),
        materials     = _merge_materials(mat_rows),
        personnel     = _merge_personnel(pers_rows),
        hse_observations = _clean_strings(hse),
        quality_checks   = _clean_strings(qc),
        issues_risks     = _clean_strings(risks),
        next_day_plan    = _clean_strings(plan),
        incidents        = " | ".join(incidents_parts),
        source_files     = [d.filename for d in docs],
    )

    report.notes.append(
        f"Merged {len(docs)} file(s) into "
        f"{len(report.work_progress)} work rows, "
        f"{len(report.equipment)} equipment rows, "
        f"{len(report.materials)} material rows, "
        f"{len(report.personnel)} personnel rows."
    )
    failed = [d for d in per_file if "_error" in d]
    if failed:
        report.notes.append(f"{len(failed)} file(s) failed extraction.")
    print(f"[agg] done. {len(report.work_progress)} work rows.", flush=True)

    emit("done", report=report)
    return report
