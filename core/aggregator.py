import json
from core.models import ExtractedDocument, AggregatedReport
from core.gemini_client import generate_text
from core.errors import GeminiError

_PROMPT = """You are a construction Daily Progress Report (DPR) analyst.
Merge the following site reports into ONE structured DPR.

Return STRICT JSON matching this schema:
{{
  "project_name": "", "report_date": "", "site_location": "",
  "prepared_by": "", "weather": "",
  "personnel_on_site": [], "work_progress": [], "equipment": [],
  "materials": [], "hse_observations": [], "incidents": "",
  "quality_checks": [], "issues_risks": [], "next_day_plan": []
}}

SOURCE REPORTS:
{docs}
"""

def aggregate(docs: list[ExtractedDocument]) -> AggregatedReport:
    blocks = []
    for d in docs:
        blocks.append(f"--- FILE: {d.filename} ---\n{d.raw_text[:12000]}")
    prompt = _PROMPT.format(docs="\n\n".join(blocks))

    raw = generate_text(prompt, json_mode=True)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        raise GeminiError(f"Gemini returned non-JSON: {e}") from e

    data.setdefault("source_files", [d.filename for d in docs])
    return AggregatedReport(**{
        k: v for k, v in data.items()
        if k in AggregatedReport.__dataclass_fields__
    })
