"""Canonical data contracts for DPR-Matrix."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------
@dataclass
class ExtractedDocument:
    filename: str
    mime: str
    sections: list[dict] = field(default_factory=list)
    raw_text: str = ""
    meta: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
@dataclass
class LineItem:
    """A single row in a structured table with provenance."""
    label: str = ""
    quantity: str = ""
    unit: str = ""
    notes: str = ""
    sources: list[str] = field(default_factory=list)
    count: int = 1

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Conflict:
    """A discrepancy flagged across source reports."""
    field: str = ""
    values: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AggregatedReport:
    # Header
    project_name: str = ""
    report_date: str = ""
    site_location: str = ""
    prepared_by: str = ""
    weather: str = ""

    # Structured rows (with provenance)
    personnel_on_site: list[dict] = field(default_factory=list)
    work_progress:     list[dict] = field(default_factory=list)
    equipment:         list[dict] = field(default_factory=list)
    materials:         list[dict] = field(default_factory=list)

    # Free-text observations
    hse_observations: list[str] = field(default_factory=list)
    quality_checks:   list[str] = field(default_factory=list)
    issues_risks:     list[str] = field(default_factory=list)
    next_day_plan:    list[str] = field(default_factory=list)

    incidents: str = ""

    # Provenance & diagnostics
    source_files: list[str] = field(default_factory=list)
    conflicts:    list[dict] = field(default_factory=list)
    notes:        list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AggregatedReport":
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in data.items() if k in allowed})
