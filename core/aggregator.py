"""Two-pass aggregator.

Pass 1 — Gemini extracts EACH file independently into the strict schema.
Pass 2 — Python merges deterministically: normalize → group → sum.

The LLM never does the merge. It reads one file at a time and returns
structured rows. All cross-file logic is Python, so it is auditable and
reproducible.
"""
from __future__ import annotations

import json
import re

from core.models import ExtractedDocument, AggregatedReport
from core.gemini_client import generate_text
from core.errors import GeminiError
from core.normalize import (
    norm_building, norm_floor, norm_activity, norm_unit,
    to_float, fmt_num,
)


# ═══════════════════════════════════════════════════════════════════════════
# THE PROMPT — production-grade, with explicit rules and examples
# ═══════════════════════════════════════════════════════════════════════════
_SYSTEM = r"""You are extracting a Daily Progress Report (DPR) from ONE source document.
The document may be a scanned page, a photo, an Excel export, or raw text.
Read it carefully and return STRICT JSON — no prose, no markdown fences.

═══════════════════════════════════════════════════════════════════════
CRITICAL RULES — READ EVERY ONE
═══════════════════════════════════════════════════════════════════════

RULE 1 — NEVER concatenate location + activity into one string.
   GOOD: {"building":"70","floor":"4","activity":"Mortar works", ...}
   BAD:  {"label":"Building No 70, Floor No 4 + 1 helper - Mortar works"}

RULE 2 — Helper counts belong in the "helpers" field. NEVER in the floor.
   Source: "Floor 4 + 1 helper"
   ✓ building="70", floor="4", helpers=1
   ✗ floor="4 + 1 helper"

RULE 3 — Skilled workers and helpers are separate counters.
   "10 workers + 3 helpers" → quantity=10, skilled=10, helpers=3, unit="workers"
   "13 masons + 2 helpers"  → quantity=13, skilled=13, helpers=2, unit="workers"
   "5 workers"              → quantity=5,  skilled=5,  helpers=0, unit="workers"
   "4"                      → quantity=4,  skilled=4,  helpers=0, unit="workers"

RULE 4 — Quantity and unit are separate fields.
   "15 m²"      → quantity=15,  unit="m2"
   "3 m³"       → quantity=3,   unit="m3"
   "200 bags"   → quantity=200, unit="bags"

RULE 5 — Building and floor are separate fields.
   "Building No 53, Floor No 2" → building="53", floor="2"
   "Bldg 59 - 3rd floor"        → building="59", floor="3"
   "B-87 F3"                    → building="87", floor="3"

RULE 6 — Normalize activity names to this controlled vocabulary:
     Mortar works · Brickworks · Sealer works · Plastering · Painting
     Tiling · Steel fixing · Concrete works · Formwork · Carpentry
     Electrical · Plumbing
   Map synonyms: "Mortaring"/"Masonry"→"Mortar works",
                 "Brick laying"/"Bricklaying"→"Brickworks",
                 "Sealing"→"Sealer works", etc.

RULE 7 — ONE row per (building, floor, activity). If the document lists the
   same combination twice, SUM the quantities and crews.

RULE 8 — Never invent data. Missing field → empty string or 0.

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
      "building": "53",
      "floor":    "2",
      "zone":     "",
      "activity": "Mortar works",
      "quantity": 5,
      "unit":     "workers",
      "skilled":  5,
      "helpers":  3,
      "progress_pct": "",
      "notes":    ""
    }
  ],

  "equipment": [
    { "name":"", "model":"", "quantity":0, "status":"", "location":"", "notes":"" }
  ],

  "materials": [
    { "name":"", "grade":"", "quantity":0, "unit":"", "location":"", "notes":"" }
  ],

  "personnel": [
    { "trade":"", "count":0, "building":"", "notes":"" }
  ],

  "hse_observations": [],
  "quality_checks":   [],
  "issues_risks":     [],
  "next_day_plan":    [],
  "incidents":        ""
}"""


def _prompt_for(doc: ExtractedDocument) -> str:
    return f"{_SYSTEM}\n\nSOURCE FILENAME: {doc.filename}\n\nDOCUMENT CONTENT:\n{doc.raw_text[:30000]}"


# ═══════════════════════════════════════════════════════════════════════════
# JSON extraction — tolerant to fences and prose
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
# PASS 1 — per-file structured extraction
# ═══════════════════════════════════════════════════════════════════════════
def _extract_one(doc: ExtractedDocument) -> dict:
    raw = generate_text(_prompt_for(doc), json_mode=True)
    data = _extract_json(raw)

    # Attach this document's filename to every row's sources
    fn = doc.filename
    for key in ("work_progress", "equipment", "materials", "personnel"):
        for row in data.get(key, []):
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

        qty   = to_float(r.get("quantity")) or 0.0
        sk    = to_float(r.get("skilled"))  or 0.0
        hp    = to_float(r.get("helpers"))  or 0.0
        unit  = norm_unit(r.get("unit", ""))
        srcs  = r.get("sources") or []
        if isinstance(srcs, str):
            srcs = [srcs]

        if key not in groups:
            groups[key] = {
                "building": b,
                "floor":    f,
                "zone":     r.get("zone", "").strip(),
                "activity": a,
                "quantity": qty,
                "skilled":  sk,
                "helpers":  hp,
                "unit":     unit,
                "progress_pct": r.get("progress_pct", "").strip(),
                "notes":    [r.get("notes", "").strip()] if r.get("notes") else [],
                "sources":  list(dict.fromkeys(srcs)),
            }
        else:
            g = groups[key]
            g["quantity"] += qty
            g["skilled"]  += sk
            g["helpers"]  += hp
            if unit and not g["unit"]:
                g["unit"] = unit
            if r.get("notes") and r["notes"].strip() not in g["notes"]:
                g["notes"].append(r["notes"].strip())
            for s in srcs:
                if s not in g["sources"]:
                    g["sources"].append(s)

    out = []
    for g in groups.values():
        g["quantity"] = fmt_num(g["quantity"])
        g["skilled"]  = fmt_num(g["skilled"])
        g["helpers"]  = fmt_num(g["helpers"])
        g["notes"]    = " | ".join(g["notes"])
        out.append(g)

    # Sort: building, floor, activity
    def key_sort(x):
        try:
            b = int(x["building"])
        except ValueError:
            b = 10**9
        try:
            f = int(x["floor"])
        except ValueError:
            f = 10**9
        return (b, f, x["activity"])
    out.sort(key=key_sort)
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
        qty = to_float(r.get("quantity")) or 1.0
        if key not in groups:
            groups[key] = {
                "name":     name,
                "model":    model,
                "quantity": qty,
                "status":   (r.get("status") or "").strip(),
                "location": (r.get("location") or "").strip(),
                "notes":    [r.get("notes", "").strip()] if r.get("notes") else [],
                "sources":  list(dict.fromkeys(srcs)),
            }
        else:
            g = groups[key]
            g["quantity"] += qty
            if r.get("notes") and r["notes"].strip() not in g["notes"]:
                g["notes"].append(r["notes"].strip())
            for s in srcs:
                if s not in g["sources"]:
                    g["sources"].append(s)
    out = []
    for g in groups.values():
        g["quantity"] = fmt_num(g["quantity"])
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
        qty = to_float(r.get("quantity")) or 0.0
        srcs = r.get("sources") or []
        if isinstance(srcs, str):
            srcs = [srcs]
        if key not in groups:
            groups[key] = {
                "name": name, "grade": grade, "quantity": qty, "unit": unit,
                "location": (r.get("location") or "").strip(),
                "notes": [r.get("notes","").strip()] if r.get("notes") else [],
                "sources": list(dict.fromkeys(srcs)),
            }
        else:
            g = groups[key]
            if unit and g["unit"] == unit:
                g["quantity"] += qty
            if r.get("notes") and r["notes"].strip() not in g["notes"]:
                g["notes"].append(r["notes"].strip())
            for s in srcs:
                if s not in g["sources"]:
                    g["sources"].append(s)
    out = []
    for g in groups.values():
        g["quantity"] = fmt_num(g["quantity"])
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
        count = to_float(r.get("count")) or 0.0
        srcs = r.get("sources") or []
        if isinstance(srcs, str):
            srcs = [srcs]
        if trade not in groups:
            groups[trade] = {
                "trade": trade, "count": count,
                "building": (r.get("building") or "").strip(),
                "notes": [r.get("notes","").strip()] if r.get("notes") else [],
                "sources": list(dict.fromkeys(srcs)),
            }
        else:
            g = groups[trade]
            g["count"] += count
            for s in srcs:
                if s not in g["sources"]:
                    g["sources"].append(s)
    out = []
    for g in groups.values():
        g["count"] = fmt_num(g["count"])
        g["notes"] = " | ".join(g["notes"])
        out.append(g)
    out.sort(key=lambda x: x["trade"])
    return out


def _clean_strings(items: list) -> list[str]:
    seen, out = set(), []
    for it in items or []:
        s = str(it).strip()
        if s and s.lower() not in seen:
            seen.add(s.lower()); out.append(s)
    return out


# ═══════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════
def aggregate(docs: list[ExtractedDocument]) -> AggregatedReport:
    if not docs:
        raise GeminiError("No documents to aggregate.")

    # Pass 1 — extract each file independently
    per_file: list[dict] = []
    for d in docs:
        try:
            per_file.append(_extract_one(d))
        except Exception as e:
            per_file.append({"_error": f"{d.filename}: {type(e).__name__}: {e}"})

    # Collect rows
    work_rows   = []
    equip_rows  = []
    mat_rows    = []
    pers_rows   = []
    hse, qc, risks, plan = [], [], [], []
    incidents_parts = []
    header: dict = {}

    for data in per_file:
        if "_error" in data:
            continue
        for r in data.get("work_progress", []) or []: work_rows.append(r)
        for r in data.get("equipment", [])     or []: equip_rows.append(r)
        for r in data.get("materials", [])     or []: mat_rows.append(r)
        for r in data.get("personnel", [])     or []: pers_rows.append(r)
        hse   += data.get("hse_observations") or []
        qc    += data.get("quality_checks")   or []
        risks += data.get("issues_risks")     or []
        plan  += data.get("next_day_plan")    or []
        if data.get("incidents"):
            incidents_parts.append(str(data["incidents"]).strip())
        # take first non-empty header value
        for k in ("project_name", "report_date", "site_location",
                  "prepared_by", "weather", "shift"):
            if not header.get(k) and data.get(k):
                header[k] = data[k]

    # Pass 2 — deterministic merge
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
    return report
