"""Statistical anomaly detection and field coverage analysis.

Pure functions over AggregatedReport — no UI, no I/O, no numpy.
"""
from __future__ import annotations

from core.normalize import to_float


# ═══════════════════════════════════════════════════════════════════════
# Small stats helpers (stdlib only)
# ═══════════════════════════════════════════════════════════════════════
def _median(vals: list[float]) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    n = len(s)
    m = n // 2
    return s[m] if n % 2 else (s[m - 1] + s[m]) / 2.0


def _quantile(vals: list[float], q: float) -> float:
    if not vals:
        return 0.0
    s = sorted(vals)
    if len(s) == 1:
        return s[0]
    pos = q * (len(s) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    frac = pos - lo
    return s[lo] * (1 - frac) + s[hi] * frac


def _iqr_bounds(vals: list[float], k: float = 1.5) -> tuple[float, float]:
    if len(vals) < 4:
        return (min(vals), max(vals)) if vals else (0.0, 0.0)
    q1 = _quantile(vals, 0.25)
    q3 = _quantile(vals, 0.75)
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr


def _fmt_n(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


# ═══════════════════════════════════════════════════════════════════════
# Anomaly detection
# ═══════════════════════════════════════════════════════════════════════
def detect_anomalies(report) -> list[dict]:
    """
    Returns a list of anomaly dicts, each:
    {type, severity, building, floor, activity, field, value,
     peer_median, ratio, reason}
    """
    out: list[dict] = []

    # ── Crew outliers (IQR) ──────────────────────────────────────────
    crews: list[tuple[dict, float]] = []
    for r in report.work_progress:
        ct = to_float(r.get("crew_total"))
        if ct is not None and ct > 0:
            crews.append((r, ct))

    if len(crews) >= 5:
        vals = [v for _, v in crews]
        lo, hi = _iqr_bounds(vals)
        med = _median(vals)
        for r, ct in crews:
            if ct > hi and med > 0 and ct >= med * 2:
                out.append({
                    "type": "crew_outlier",
                    "severity": "soft",
                    "building": r.get("building", ""),
                    "floor": r.get("floor", ""),
                    "activity": r.get("activity", ""),
                    "field": "crew_total",
                    "value": _fmt_n(ct),
                    "peer_median": _fmt_n(med),
                    "ratio": round(ct / med, 2),
                    "reason": (
                        f"crew {_fmt_n(ct)} is {ct / med:.1f}× "
                        f"median ({_fmt_n(med)})"
                    ),
                })

    # ── Quantity outliers within same activity ───────────────────────
    by_act: dict[str, list[tuple[dict, float]]] = {}
    for r in report.work_progress:
        act = (r.get("activity") or "").strip()
        q = to_float(r.get("quantity"))
        if act and q is not None and q > 0:
            by_act.setdefault(act, []).append((r, q))

    for act, rows in by_act.items():
        if len(rows) < 4:
            continue
        vals = [v for _, v in rows]
        _, hi = _iqr_bounds(vals)
        med = _median(vals)
        for r, q in rows:
            if q > hi and med > 0 and q >= med * 2:
                out.append({
                    "type": "quantity_outlier",
                    "severity": "soft",
                    "building": r.get("building", ""),
                    "floor": r.get("floor", ""),
                    "activity": act,
                    "field": "quantity",
                    "value": _fmt_n(q),
                    "peer_median": _fmt_n(med),
                    "ratio": round(q / med, 2),
                    "reason": (
                        f"{act} quantity {_fmt_n(q)} is {q / med:.1f}× "
                        f"median ({_fmt_n(med)})"
                    ),
                })

    # ── Coverage gap: personnel building not in work progress ────────
    wp_b = {
        (r.get("building") or "").strip()
        for r in report.work_progress
        if (r.get("building") or "").strip()
    }
    pers_b = {
        (p.get("building") or "").strip()
        for p in report.personnel
        if (p.get("building") or "").strip()
    }
    for b in sorted(pers_b - wp_b):
        out.append({
            "type": "coverage_gap",
            "severity": "soft",
            "building": b,
            "floor": "",
            "activity": "",
            "field": "building",
            "value": b,
            "peer_median": "",
            "ratio": 0,
            "reason": (
                f"Building {b} appears in personnel section "
                f"but not in work progress"
            ),
        })

    # ── Low-confidence rows ──────────────────────────────────────────
    for r in report.work_progress:
        if r.get("confidence") == "low":
            out.append({
                "type": "low_confidence",
                "severity": "soft",
                "building": r.get("building", ""),
                "floor": r.get("floor", ""),
                "activity": r.get("activity", ""),
                "field": "confidence",
                "value": "low",
                "peer_median": "",
                "ratio": 0,
                "reason": (
                    "row has low confidence — sources disagreed "
                    "or only a single low-reliability source"
                ),
            })

    return out


# ═══════════════════════════════════════════════════════════════════════
# Coverage analysis
# ═══════════════════════════════════════════════════════════════════════
_COVERAGE_FIELDS = [
    ("skilled",      "Skilled crew"),
    ("helpers",      "Helpers"),
    ("quantity",     "Quantity"),
    ("unit",         "Unit"),
    ("zone",         "Zone"),
    ("progress_pct", "Progress %"),
    ("notes",        "Notes"),
]


def compute_coverage(report) -> dict:
    rows = report.work_progress
    n = len(rows)

    fields = []
    for key, label in _COVERAGE_FIELDS:
        count = sum(1 for r in rows if str(r.get(key) or "").strip())
        fields.append({
            "name": key,
            "label": label,
            "count": count,
            "total": n,
            "pct": round(count / n * 100, 1) if n else 0.0,
        })

    wp_b = {
        (r.get("building") or "").strip()
        for r in rows
        if (r.get("building") or "").strip()
    }
    pers_b = {
        (p.get("building") or "").strip()
        for p in report.personnel
        if (p.get("building") or "").strip()
    }

    return {
        "work_rows": n,
        "fields": fields,
        "buildings_in_work": len(wp_b),
        "buildings_in_personnel": len(pers_b),
        "missing_buildings": sorted(pers_b - wp_b),
    }
