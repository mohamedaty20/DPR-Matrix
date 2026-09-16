"""Data quality engine.

Source reliability, tolerance bands, confidence scoring, quality metrics.
Pure functions — no UI, no I/O, no external dependencies.
"""
from __future__ import annotations

from dataclasses import dataclass


# ═══════════════════════════════════════════════════════════════════════
# Source reliability
# ═══════════════════════════════════════════════════════════════════════
# File-type base reliability: official exports > spreadsheets > plain text > photos
_BASE_BY_EXT: dict[str, float] = {
    ".pdf":  1.00,
    ".xlsx": 0.85,
    ".xls":  0.85,
    ".txt":  0.70,
    ".png":  0.55,
    ".jpg":  0.55,
    ".jpeg": 0.55,
}

_SCHEMA_SCALARS = ("project_name", "report_date", "site_location",
                   "prepared_by", "weather", "shift", "incidents")
_SCHEMA_TABLES  = ("work_progress", "equipment", "materials", "personnel")
_SCHEMA_LISTS   = ("hse_observations", "quality_checks",
                   "issues_risks", "next_day_plan")


def _ext(filename: str) -> str:
    fn = (filename or "").lower()
    return "." + fn.rsplit(".", 1)[-1] if "." in fn else ""


def source_reliability(filename: str, data: dict) -> float:
    """0.0 – 1.0. 60% file type, 40% extraction completeness."""
    base = _BASE_BY_EXT.get(_ext(filename), 0.5)

    total = len(_SCHEMA_SCALARS) + len(_SCHEMA_TABLES) + len(_SCHEMA_LISTS)
    scored = 0
    for k in _SCHEMA_SCALARS:
        if str(data.get(k) or "").strip():
            scored += 1
    for k in _SCHEMA_TABLES:
        if data.get(k):
            scored += 1
    for k in _SCHEMA_LISTS:
        if data.get(k):
            scored += 1
    completeness = scored / total if total else 0.0

    return round(0.6 * base + 0.4 * completeness, 3)


# ═══════════════════════════════════════════════════════════════════════
# Tolerance
# ═══════════════════════════════════════════════════════════════════════
DEFAULT_TOLERANCE = 0.15   # ≤ 15% difference = agreement


def within_tolerance(a: float, b: float,
                     pct: float = DEFAULT_TOLERANCE) -> bool:
    if a == b:
        return True
    mx = max(abs(a), abs(b))
    if mx == 0:
        return True
    return abs(a - b) / mx <= pct


def values_agree(values: list[float],
                 pct: float = DEFAULT_TOLERANCE) -> bool:
    """True if every pair of values is within tolerance."""
    if len(values) <= 1:
        return True
    lo, hi = min(values), max(values)
    if lo == 0 and hi == 0:
        return True
    mx = max(abs(lo), abs(hi))
    return (abs(hi - lo) / mx) <= pct if mx else True


# ═══════════════════════════════════════════════════════════════════════
# Confidence
# ═══════════════════════════════════════════════════════════════════════
HIGH   = "high"
MEDIUM = "medium"
LOW    = "low"

_ORDER = {HIGH: 0, MEDIUM: 1, LOW: 2}


def confidence_for_field(
    per_source: dict[str, float],
    reliabilities: dict[str, float],
    *,
    tolerance: float = DEFAULT_TOLERANCE,
) -> str:
    """Classify confidence in a merged numeric value."""
    if not per_source:
        return LOW

    n = len(per_source)
    vals = list(per_source.values())

    # Single source — confidence tracks reliability tier
    if n == 1:
        src = next(iter(per_source))
        r = reliabilities.get(src, 0.5)
        if r >= 0.85:
            return HIGH
        if r >= 0.65:
            return MEDIUM
        return LOW

    # Multiple sources, all agree → high
    if values_agree(vals, tolerance):
        return HIGH

    # Multiple sources, disagreement → majority band check
    max_v = max(vals)
    in_band = sum(1 for v in vals if within_tolerance(v, max_v, tolerance))
    if in_band >= 2 and n >= 3:
        return MEDIUM   # majority agree, one outlier

    return LOW


def worst_confidence(a: str, b: str) -> str:
    return a if _ORDER.get(a, 2) >= _ORDER.get(b, 2) else b


# ═══════════════════════════════════════════════════════════════════════
# Reliability-weighted resolution
# ═══════════════════════════════════════════════════════════════════════
def resolve_with_reliability(
    per_source: dict[str, float],
    reliabilities: dict[str, float],
    *,
    tolerance: float = DEFAULT_TOLERANCE,
) -> tuple[float | None, str]:
    """
    Pick a canonical value for a field.
    Returns (value, reason).

    Rules (in order):
      1. Empty              → (None, "no data")
      2. Single source      → that value
      3. All agree          → max
      4. One source ≥0.20 more reliable than all others → trust it
      5. Otherwise          → max (conservative)
    """
    if not per_source:
        return None, "no data"

    vals = list(per_source.values())
    if len(vals) == 1:
        return vals[0], "single source"

    if values_agree(vals, tolerance):
        return max(vals), "all sources within tolerance"

    ranked = sorted(
        per_source.items(),
        key=lambda kv: (-reliabilities.get(kv[0], 0.5), kv[0]),
    )
    top_src, top_val = ranked[0]
    top_r = reliabilities.get(top_src, 0.5)
    others = [reliabilities.get(s, 0.5) for s, _ in ranked[1:]]

    if others and top_r - max(others) >= 0.20:
        return top_val, f"trusted {top_src} (reliability {top_r:.2f})"

    return max(vals), "sources disagree — using max (conservative)"


# ═══════════════════════════════════════════════════════════════════════
# Composite quality score
# ═══════════════════════════════════════════════════════════════════════
@dataclass(frozen=True)
class QualityScore:
    score:         int      # 0-100
    grade:         str      # A / B / C / D
    completeness:  float    # 0-1
    confidence:    float    # 0-1
    corroboration: float    # 0-1
    consistency:   float    # 0-1
    n_high:        int
    n_medium:      int
    n_low:         int
    n_soft:        int
    n_hard:        int


def _grade(score: int) -> str:
    if score >= 85: return "A"
    if score >= 70: return "B"
    if score >= 55: return "C"
    return "D"


def compute_quality(report) -> QualityScore:
    """Composite quality score derived from the aggregated report."""
    # Completeness
    scalar_keys = ("project_name", "report_date", "site_location",
                   "prepared_by", "weather", "shift", "incidents")
    filled = sum(
        1 for k in scalar_keys
        if str(getattr(report, k, "") or "").strip()
    )
    tables_present = sum(
        1 for k in ("work_progress", "equipment", "materials", "personnel")
        if getattr(report, k, None)
    )
    total_fields = len(scalar_keys) + 4
    filled += tables_present
    completeness = filled / total_fields if total_fields else 0.0

    # Confidence distribution
    n_high = n_med = n_low = 0
    for r in report.work_progress:
        c = r.get("confidence", LOW)
        if c == HIGH:      n_high += 1
        elif c == MEDIUM:  n_med  += 1
        else:              n_low  += 1
    n = n_high + n_med + n_low
    confidence = ((n_high * 1.0 + n_med * 0.6 + n_low * 0.2) / n) if n else 0.0

    # Corroboration
    src_counts = [len(r.get("sources", [])) for r in report.work_progress]
    avg_src = sum(src_counts) / len(src_counts) if src_counts else 0.0
    corroboration = min(avg_src / 3.0, 1.0)

    # Consistency — penalize conflicts
    n_rows = len(report.work_progress) or 1
    n_soft = sum(1 for c in report.conflicts if c.get("severity") == "soft")
    n_hard = sum(1 for c in report.conflicts if c.get("severity") == "hard")
    penalty = (n_soft * 0.3 + n_hard * 1.0) / n_rows
    consistency = max(0.0, 1.0 - penalty)

    raw = (completeness  * 0.40
           + confidence   * 0.30
           + corroboration * 0.15
           + consistency  * 0.15)
    score = int(round(raw * 100))

    return QualityScore(
        score=score,
        grade=_grade(score),
        completeness=completeness,
        confidence=confidence,
        corroboration=corroboration,
        consistency=consistency,
        n_high=n_high, n_medium=n_med, n_low=n_low,
        n_soft=n_soft, n_hard=n_hard,
    )
