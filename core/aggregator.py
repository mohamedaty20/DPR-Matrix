"""Aggregation engine.

Pass 1 — Gemini merges raw text into structured JSON.
Pass 2 — deterministic Python post-processing:
  • de-duplicate line items by (label, unit)
  • attach source attribution
  • detect header-level conflicts
  • strip empties

NOTE: LineItem and Conflict live in core/models.py — this module imports them.
      Never re-define them here.
"""
from __future__ import annotations

import json
import re

from core.models import ExtractedDocument, AggregatedReport
from core.gemini_client import generate_text
from core.errors import GeminiError


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------
_SYSTEM = """You are a senior construction DPR analyst.
You will receive MULTIPLE site reports from the SAME day at the SAME project.
Merge them into ONE canonical Daily Progress Report.

Rules:
1. De-duplicate: if the same equipment/person/material appears in multiple
   reports, list it ONCE.
2. Attribute: for every row, list which source files it came from.
3. Flag conflicts: if two reports disagree (weather, personnel count,
   progress %), record the discrepancy in "conflicts".
4. Be literal: transcribe quantities, IDs, and names exactly.
5. Never invent data. If a field is unknown, leave it empty.

Return STRICT JSON matching this schema — no prose, no markdown fences:

{
  "project_name": "",
  "report_date":  "YYYY-MM-DD or as written",
  "site_location": "",
  "prepared_by":  "",
  "weather":      "",
  "personnel_on_site": [{"label":"","quantity":"","unit":"","notes":"","sources":["file.pdf"]}],
  "work_progress":     [{"label":"","quantity":"","unit":"","notes":"","sources":["file.pdf"]}],
  "equipment":         [{"label":"","quantity":"","unit":"","notes":"","sources":["file.pdf"]}],
  "materials":         [{"label":"","quantity":"","unit":"","notes":"","sources":["file.pdf"]}],
  "hse_observations":  ["..."],
  "quality_checks":    ["..."],
  "issues_risks":      ["..."],
  "next_day_plan":     ["..."],
  "incidents":         "",
  "conflicts":         [{"field":"","values":[],"sources":[]}]
}"""


def _format_doc(d: ExtractedDocument) -> str:
    body = d.raw_text[:14000]
    return f"<<<FILE: {d.filename}>>>\n{body}\n<<<END>>>"


def _build_prompt(docs: list[ExtractedDocument]) -> str:
    blocks = "\n\n".join(_format_doc(d) for d in docs)
    filenames = ", ".join(d.filename for d in docs)
    return (
        f"{_SYSTEM}\n\n"
        f"SOURCE FILES ({len(docs)}): {filenames}\n\n"
        f"REPORTS:\n{blocks}"
    )


# ---------------------------------------------------------------------------
# JSON extraction — tolerant to fences and trailing prose
# ---------------------------------------------------------------------------
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _extract_json(raw: str) -> dict:
    if not raw:
        raise GeminiError("Gemini returned an empty response.")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    m = _FENCE.search(raw)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise GeminiError(f"Gemini returned non-JSON output ({len(raw)} chars).")


# ---------------------------------------------------------------------------
# Deterministic post-processing
# ---------------------------------------------------------------------------
def _norm_key(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def _fmt_num(n: float) -> str:
    return str(int(n)) if float(n).is_integer() else f"{n:.2f}".rstrip("0").rstrip(".")


def _dedupe_rows(rows: list[dict], source_file: str | None) -> list[dict]:
    grouped: dict[tuple[str, str], dict] = {}

    for r in rows or []:
        if not isinstance(r, dict):
            continue
        label = _norm_key(r.get("label", ""))
        unit = _norm_key(r.get("unit", ""))
        if not label:
            continue
        key = (label, unit)

        sources = r.get("sources") or []
        if isinstance(sources, str):
            sources = [sources]
        if source_file and source_file not in sources:
            sources.append(source_file)

        qty_raw = str(r.get("quantity", "") or "").strip()
        try:
            qty_num = float(re.sub(r"[^\d.\-]", "", qty_raw)) if qty_raw else None
        except ValueError:
            qty_num = None

        if key not in grouped:
            grouped[key] = {
                "label": r.get("label", "").strip(),
                "quantity": qty_raw,
                "unit": r.get("unit", "").strip(),
                "notes": r.get("notes", "").strip(),
                "sources": list(dict.fromkeys(sources)),
                "count": 1,
                "_num": qty_num,
            }
        else:
            g = grouped[key]
            if qty_num is not None and g["_num"] is not None:
                g["_num"] += qty_num
                g["quantity"] = _fmt_num(g["_num"])
            elif qty_raw and not g["quantity"]:
                g["quantity"] = qty_raw
            if r.get("notes") and r["notes"] not in g["notes"]:
                g["notes"] = (g["notes"] + " | " + r["notes"]).strip(" |")
            for s in sources:
                if s not in g["sources"]:
                    g["sources"].append(s)
            g["count"] += 1

    out = []
    for g in grouped.values():
        g.pop("_num", None)
        out.append(g)
    return out


def _clean_strings(items: list) -> list[str]:
    seen, out = set(), []
    for it in items or []:
        s = str(it).strip()
        k = _norm_key(s)
        if s and k not in seen:
            seen.add(k); out.append(s)
    return out


def _detect_header_conflicts(raw: dict, docs: list[ExtractedDocument]) -> list[dict]:
    conflicts = list(raw.get("conflicts") or [])
    for f in ("weather", "prepared_by", "site_location", "report_date"):
        vals = set()
        for d in docs:
            v = (d.meta.get(f) or "").strip()
            if v:
                vals.add(v)
        if len(vals) > 1:
            conflicts.append({
                "field": f,
                "values": sorted(vals),
                "sources": [d.filename for d in docs],
            })

    seen, clean = set(), []
    for c in conflicts:
        if not isinstance(c, dict):
            continue
        key = (c.get("field", ""), tuple(sorted(c.get("values", []))))
        if key in seen:
            continue
        seen.add(key); clean.append(c)
    return clean


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def aggregate(docs: list[ExtractedDocument]) -> AggregatedReport:
    if not docs:
        raise GeminiError("No documents to aggregate.")

    prompt = _build_prompt(docs)

    try:
        raw = generate_text(prompt, json_mode=True)
        data = _extract_json(raw)
    except GeminiError:
        raise
    except Exception as e:
        raise GeminiError(f"Aggregation call failed: {e}") from e

    single_source = docs[0].filename if len(docs) == 1 else None

    report = AggregatedReport(
        project_name  = (data.get("project_name") or "").strip(),
        report_date   = (data.get("report_date")  or "").strip(),
        site_location = (data.get("site_location") or "").strip(),
        prepared_by   = (data.get("prepared_by")  or "").strip(),
        weather       = (data.get("weather")      or "").strip(),
        personnel_on_site = _dedupe_rows(data.get("personnel_on_site"), single_source),
        work_progress     = _dedupe_rows(data.get("work_progress"),     single_source),
        equipment         = _dedupe_rows(data.get("equipment"),         single_source),
        materials         = _dedupe_rows(data.get("materials"),         single_source),
        hse_observations  = _clean_strings(data.get("hse_observations")),
        quality_checks    = _clean_strings(data.get("quality_checks")),
        issues_risks      = _clean_strings(data.get("issues_risks")),
        next_day_plan     = _clean_strings(data.get("next_day_plan")),
        incidents         = (data.get("incidents") or "").strip(),
        source_files      = [d.filename for d in docs],
        conflicts         = _detect_header_conflicts(data, docs),
    )

    report.notes.append(
        f"Merged {len(docs)} file(s); "
        f"{sum(len(getattr(report, f)) for f in (
            'work_progress','equipment','materials','personnel_on_site'
        ))} structured rows after de-duplication."
    )
    if report.conflicts:
        report.notes.append(f"{len(report.conflicts)} conflict(s) flagged.")

    return report
