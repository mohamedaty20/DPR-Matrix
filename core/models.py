from dataclasses import dataclass, field, asdict
from typing import Any

@dataclass
class ExtractedDocument:
    filename: str
    mime: str
    sections: list[dict] = field(default_factory=list)
    raw_text: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

@dataclass
class AggregatedReport:
    project_name: str = ""
    report_date: str = ""
    site_location: str = ""
    prepared_by: str = ""
    weather: str = ""
    personnel_on_site: list[str] = field(default_factory=list)
    work_progress: list[dict] = field(default_factory=list)
    equipment: list[dict] = field(default_factory=list)
    materials: list[dict] = field(default_factory=list)
    hse_observations: list[str] = field(default_factory=list)
    incidents: str = ""
    quality_checks: list[str] = field(default_factory=list)
    issues_risks: list[str] = field(default_factory=list)
    next_day_plan: list[str] = field(default_factory=list)
    source_files: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
