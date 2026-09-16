"""Analytics engine.

Pure functions over AggregatedReport. No UI, no I/O, no dependencies.
Every metric here is derived from real report data — nothing is hardcoded.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from core.normalize import to_float


# ── Formatting helpers ───────────────────────────────────────────────────
def fmt_count(n: float | int) -> str:
    n = float(n)
    if n >= 1_000_000: return f"{n / 1_000_000:.1f}M"
    if n >= 10_000:    return f"{n / 1_000:.0f}K"
    if n >= 1_000:     return f"{n / 1_000:.1f}K"
    return str(int(n)) if n.is_integer() else f"{n:g}"


def fmt_pct(v: float) -> str:
    return f"{v:.0f}%"


# ── Manpower ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Manpower:
    skilled: int
    helpers: int
    total: int
    skilled_pct: float
    helpers_pct: float
    buildings_with_crew: int
    avg_per_building: float
    peak_building: str
    peak_building_count: int
    by_building: list[tuple[str, int]]        # descending by count


def manpower(report) -> Manpower:
    sk = hp = 0
    by_bldg: dict[str, int] = defaultdict(int)

    for r in report.work_progress:
        s = int(to_float(r.get("skilled")) or 0)
        h = int(to_float(r.get("helpers")) or 0)
        sk += s; hp += h
        b = (r.get("building") or "—").strip() or "—"
        by_bldg[b] += s + h

    total = sk + hp
    sk_pct = (sk / total * 100) if total else 0.0
    hp_pct = (hp / total * 100) if total else 0.0

    items = sorted(
        by_bldg.items(),
        key=lambda kv: (-kv[1], kv[0]),
    )
    peak_name, peak_count = (items[0] if items else ("—", 0))

    return Manpower(
        skilled=sk,
        helpers=hp,
        total=total,
        skilled_pct=sk_pct,
        helpers_pct=hp_pct,
        buildings_with_crew=len(by_bldg),
        avg_per_building=(total / len(by_bldg)) if by_bldg else 0.0,
        peak_building=peak_name,
        peak_building_count=peak_count,
        by_building=items,
    )


# ── Activities ───────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Activities:
    distinct: int
    total_locations: int
    top_activity: str
    top_activity_count: int
    by_activity: list[tuple[str, int]]        # descending
    by_building: dict[str, list[tuple[str, int]]]  # building → activities


def activities(report) -> Activities:
    counter: Counter = Counter()
    by_bldg: dict[str, Counter] = defaultdict(Counter)

    for r in report.work_progress:
        a = (r.get("activity") or "").strip()
        if not a:
            continue
        b = (r.get("building") or "—").strip() or "—"
        counter[a] += 1
        by_bldg[b][a] += 1

    items = counter.most_common()
    top = items[0] if items else ("—", 0)

    return Activities(
        distinct=len(counter),
        total_locations=sum(counter.values()),
        top_activity=top[0],
        top_activity_count=top[1],
        by_activity=items,
        by_building={
            b: c.most_common()
            for b, c in sorted(by_bldg.items(), key=lambda kv: kv[0])
        },
    )


# ── Progress ─────────────────────────────────────────────────────────────
_BUCKETS = [
    ("Not started",  0.0,   0.01),
    ("Early",        0.01,  25.0),
    ("Mid",          25.0,  50.0),
    ("Advanced",     50.0,  75.0),
    ("Near complete",75.0,  99.5),
    ("Complete",     99.5, 1000.0),
]


@dataclass(frozen=True)
class Progress:
    reported: int
    total_rows: int
    avg_pct: float
    max_pct: float
    min_pct: float
    buckets: list[tuple[str, int]]           # [(label, count), ...]
    distribution_pct: list[float]            # same order as buckets


def progress(report) -> Progress:
    values: list[float] = []
    for r in report.work_progress:
        v = to_float(r.get("progress_pct"))
        if v is not None:
            values.append(max(0.0, min(100.0, v)))

    counts: dict[str, int] = {label: 0 for label, _, _ in _BUCKETS}
    for v in values:
        for label, lo, hi in _BUCKETS:
            if lo <= v < hi:
                counts[label] += 1
                break

    total = len(report.work_progress)
    n = len(values)
    avg = (sum(values) / n) if n else 0.0
    hi = max(values) if values else 0.0
    lo = min(values) if values else 0.0

    buckets = [(label, counts[label]) for label, _, _ in _BUCKETS]
    dist_pct = [
        (c / n * 100) if n else 0.0
        for _, c in buckets
    ]

    return Progress(
        reported=n,
        total_rows=total,
        avg_pct=avg,
        max_pct=hi,
        min_pct=lo,
        buckets=buckets,
        distribution_pct=dist_pct,
    )


# ── Crew efficiency (skilled / total per building) ───────────────────────
def crew_efficiency(report) -> list[tuple[str, float, float, float]]:
    """
    Returns [(building, skilled_pct, helpers_pct, total_crew), ...]
    descending by total crew. Skilled% + helpers% = 100 per row.
    """
    by_bldg: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for r in report.work_progress:
        b = (r.get("building") or "—").strip() or "—"
        s = int(to_float(r.get("skilled")) or 0)
        h = int(to_float(r.get("helpers")) or 0)
        by_bldg[b][0] += s
        by_bldg[b][1] += h

    out = []
    for b, (s, h) in by_bldg.items():
        total = s + h
        if total == 0:
            continue
        out.append((
            b,
            s / total * 100,
            h / total * 100,
            float(total),
        ))
    out.sort(key=lambda t: -t[3])
    return out


# ── Zone density ─────────────────────────────────────────────────────────
def zone_density(report) -> list[tuple[str, int]]:
    c: Counter = Counter()
    for r in report.work_progress:
        z = (r.get("zone") or "").strip()
        if z:
            c[z] += 1
    return c.most_common(8)


# ── Equipment status ─────────────────────────────────────────────────────
def equipment_status(report) -> list[tuple[str, int]]:
    c: Counter = Counter()
    for r in report.equipment:
        s = (r.get("status") or "").strip().title()
        if s:
            c[s] += 1
    return c.most_common()


# ── Materials ────────────────────────────────────────────────────────────
def materials_top(report, n: int = 8) -> list[tuple[str, float, str]]:
    """Top N materials by quantity. [(name, quantity, unit), ...]"""
    rows = []
    for r in report.materials:
        name = (r.get("name") or "").strip()
        q = to_float(r.get("quantity"))
        u = (r.get("unit") or "").strip()
        if name and q is not None:
            rows.append((name, q, u))
    rows.sort(key=lambda t: -t[1])
    return rows[:n]


# ── Conflict severity ────────────────────────────────────────────────────
def conflict_severity(report) -> str:
    """Rough severity classification for the KPI tone."""
    n = len(report.conflicts)
    if n == 0: return "clean"
    if n <= 2: return "low"
    if n <= 5: return "medium"
    return "high"


# ── Building × Activity matrix ───────────────────────────────────────────
def activity_matrix(report, top_n_acts: int = 6) -> dict:
    """
    Returns:
      {
        "activities": [a1, a2, ...],     # top N by total
        "buildings": [b1, b2, ...],
        "matrix": {building: {activity: count}},
        "max": int,                       # max cell value for shading
      }
    """
    bldg_act: dict[str, Counter] = defaultdict(Counter)
    act_total: Counter = Counter()

    for r in report.work_progress:
        b = (r.get("building") or "—").strip() or "—"
        a = (r.get("activity") or "").strip()
        if not a:
            continue
        bldg_act[b][a] += 1
        act_total[a] += 1

    top_acts = [a for a, _ in act_total.most_common(top_n_acts)]

    # Rank buildings by total activity count
    bldg_rank = sorted(
        bldg_act.items(),
        key=lambda kv: (-sum(kv[1].values()), kv[0]),
    )
    top_bldgs = [b for b, _ in bldg_rank]

    matrix = {b: dict(bldg_act[b]) for b in top_bldgs}
    mx = max(
        (v for row in matrix.values() for v in row.values()),
        default=0,
    )

    return {
        "activities": top_acts,
        "buildings": top_bldgs,
        "matrix": matrix,
        "max": mx,
    }
