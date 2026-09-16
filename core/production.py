"""Cumulative quantity / S-curve engine.

Builds planned vs actual cumulative curves per activity across reports.
Targets come from user input (session storage). Plan shape = cosine S-curve
(0% at start, 100% at end, smooth middle — standard construction profile).
"""
from __future__ import annotations

import math
from datetime import date, datetime

from core.normalize import to_float


# ── Date helpers ──────────────────────────────────────────────────────────
def _parse_date(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
        try:
            return datetime.strptime(s[:len(fmt) + 4].strip(), fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        return None


def _fmt(d: date) -> str:
    return d.strftime("%m-%d")


# ── Daily quantities per activity ─────────────────────────────────────────
def daily_quantities(reports: list[dict]) -> dict[str, list[tuple[date, float]]]:
    """{activity: [(date, qty), ...] sorted ascending by date}"""
    acc: dict[str, list[tuple[date, float]]] = {}
    for e in reports:
        d = _parse_date(e.get("report_date") or e.get("created_at", ""))
        if d is None:
            continue
        rpt = e["report"]
        for r in rpt.work_progress:
            act = (r.get("activity") or "").strip()
            q = to_float(r.get("quantity"))
            if act and q and q > 0:
                acc.setdefault(act, []).append((d, q))

    for act in acc:
        acc[act].sort(key=lambda t: t[0])
    return acc


# ── Plan shape ────────────────────────────────────────────────────────────
def _planned_curve(start: date, end: date, target: float,
                   n_points: int) -> list[float]:
    """Cosine S-curve: 0 at start, target at end."""
    if n_points <= 1:
        return [target]
    out = []
    total_days = max((end - start).days, 1)
    for i in range(n_points):
        frac_day = total_days * (i / (n_points - 1))
        x = frac_day / total_days
        s = (1 - math.cos(math.pi * x)) / 2.0
        out.append(target * s)
    return out


# ── Main entry ────────────────────────────────────────────────────────────
def build_curve(
    activity: str,
    reports: list[dict],
    *,
    target_total: float,
    start_date: str,
    end_date: str,
) -> dict:
    """
    Returns {
      "activity": str,
      "actual":    [(label, cum_value), ...],
      "planned":   [(label, planned_value), ...],
      "x_labels":  [label, ...],
      "today_cum": float,
      "today_planned": float,
      "variance_pct": float,   # (actual - planned) / planned * 100
      "target": float,
    }
    """
    dq = daily_quantities(reports)
    points = dq.get(activity, [])

    start = _parse_date(start_date)
    end = _parse_date(end_date)
    if start is None or end is None or end < start:
        return _empty(activity, target_total)

    # Collect all dates we care about: plan span + actual days within span
    all_dates: set[date] = set()
    span_days = (end - start).days + 1
    for i in range(span_days):
        all_dates.add(date.fromordinal(start.toordinal() + i))
    for d, _ in points:
        if start <= d <= end:
            all_dates.add(d)

    dates_sorted = sorted(all_dates)
    if not dates_sorted:
        return _empty(activity, target_total)

    # Actual cumulative — carry forward through gaps
    cum = 0.0
    cumulative_by_date: dict[date, float] = {}
    for d, q in points:
        if d < start:
            cum += q
        elif d <= end:
            cum += q
            cumulative_by_date[d] = cum

    actual: list[tuple[str, float]] = []
    running = cumulative_by_date.get(dates_sorted[0], 0.0) \
              if dates_sorted[0] in cumulative_by_date else 0.0
    for d in dates_sorted:
        if d in cumulative_by_date:
            running = cumulative_by_date[d]
        actual.append((_fmt(d), round(running, 2)))

    # Planned curve — same number of points
    planned_vals = _planned_curve(start, end, target_total, len(dates_sorted))
    planned = [(_fmt(d), round(v, 2)) for d, v in zip(dates_sorted, planned_vals)]

    today_cum = actual[-1][1] if actual else 0.0
    today_planned = planned[-1][1] if planned else 0.0
    var_pct = (
        ((today_cum - today_planned) / today_planned * 100)
        if today_planned > 0 else 0.0
    )

    return {
        "activity": activity,
        "actual": actual,
        "planned": planned,
        "x_labels": [_fmt(d) for d in dates_sorted],
        "today_cum": round(today_cum, 2),
        "today_planned": round(today_planned, 2),
        "variance_pct": round(var_pct, 1),
        "target": target_total,
    }


def _empty(activity: str, target: float) -> dict:
    return {
        "activity": activity, "actual": [], "planned": [],
        "x_labels": [], "today_cum": 0.0, "today_planned": 0.0,
        "variance_pct": 0.0, "target": target,
    }
