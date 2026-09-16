"""AI-powered risk & bottleneck forecast across recent reports.

The LLM only reads. It never writes to the merge or alters any report data.
"""
from __future__ import annotations

import json
import re

from core.gemini_client import generate_text
from core.errors import GeminiError
from core.history import extract_signals


_SYSTEM = r"""You are a senior construction project manager reviewing the
last several Daily Progress Reports (DPRs) from one site.

Your job: identify RISKS and BOTTLENECKS that could cause schedule slip,
cost overrun, or quality/safety non-compliance. Reason from standard civil
engineering practice — typical productivity rates, curing periods, quality
compliance, workforce continuity.

INPUT: array of daily summaries, newest last. Fields:
  date, project, weather, shift, manpower{skilled,helpers,total},
  distinct_activities, distinct_buildings, quantities{activity: qty},
  hse_observations[], quality_checks[], issues_risks[], incidents,
  next_day_plan[], conflicts (source-file disagreements).

RULES:
1. Base every claim on the DATA. Cite specific days when you reference a trend.
2. Do NOT invent numbers. Do NOT assume a schedule you were not given.
3. If data is too thin (fewer than 2 days, or missing key fields), say so
   and return overall_risk="insufficient_data" with an empty risks list.
4. Look specifically for:
   - Manpower volatility (day-to-day swings > 30%)
   - Activities that appear once then vanish (stalled work)
   - Repeat HSE observations (systemic safety issue)
   - Repeat quality flags (compliance risk)
   - Weather patterns causing recurring delays
   - Recurring conflicts across source files (reporting integrity)
   - Incidents — always escalate severity
5. Severity scale: low / medium / high. Reserve "high" for issues that
   could stop work or breach a compliance obligation.
6. Recommendations must be SPECIFIC and ACTIONABLE ("verify cube test
   results for Building 53 pour on 2026-09-14"), never generic.

OUTPUT STRICT JSON:
{
  "overall_risk": "low|medium|high|insufficient_data",
  "summary": "2-3 sentence executive summary",
  "risks": [
    {
      "category": "schedule|quality|resource|weather|safety|reporting",
      "severity": "low|medium|high",
      "title": "short title under 60 chars",
      "detail": "2-3 sentences explaining the risk",
      "evidence": "which days / values in the data suggest it",
      "recommendation": "specific action"
    }
  ],
  "bottlenecks": [
    {"building": "", "activity": "", "reason": "1 sentence"}
  ]
}

Return JSON only, no markdown fences."""


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def _extract_json(raw: str) -> dict:
    if not raw:
        raise GeminiError("Risk analysis: empty response.")
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
    raise GeminiError(f"Risk analysis: non-JSON response ({len(raw)} chars).")


def _normalize(data: dict) -> dict:
    data.setdefault("overall_risk", "insufficient_data")
    data.setdefault("summary", "")
    data.setdefault("risks", [])
    data.setdefault("bottlenecks", [])

    sev_order = {"high": 0, "medium": 1, "low": 2}
    data["risks"] = sorted(
        (r for r in data["risks"] if isinstance(r, dict)),
        key=lambda r: sev_order.get(r.get("severity", "low"), 3),
    )
    return data


def analyze(reports: list[dict]) -> dict:
    """reports is the output of core.history.load_recent()."""
    signals = extract_signals(reports)
    if not signals:
        return {
            "overall_risk": "insufficient_data",
            "summary": "No prior reports available for analysis.",
            "risks": [], "bottlenecks": [],
        }

    prompt = _SYSTEM + "\n\nDATA:\n" + json.dumps(
        signals, ensure_ascii=False, indent=2, default=str,
    )
    raw = generate_text(prompt, json_mode=True)
    return _normalize(_extract_json(raw))
