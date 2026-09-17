"""Canonical data contracts for DPR-Matrix."""
from __future__ import annotations
from dataclasses import dataclass, field as dc_field, asdict
from typing import Any


@dataclass
class ExtractedDocument:
    filename: str
    mime: str
    sections: list[dict] = dc_field(default_factory=list)
    raw_text: str = ""
    meta: dict[str, Any] = dc_field(default_factory=dict)


@dataclass
class AggregatedReport:
    # ---- Header ----
    project_name: str = ""
    report_date: str = ""
    site_location: str = ""
    prepared_by: str = ""
    weather: str = ""
    shift: str = ""

    # ---- Structured tables (list of dicts) ----
    work_progress: list[dict] = dc_field(default_factory=list)
    equipment:     list[dict] = dc_field(default_factory=list)
    materials:     list[dict] = dc_field(default_factory=list)
    personnel:     list[dict] = dc_field(default_factory=list)

    # ---- Free-text observations ----
    hse_observations: list[str] = dc_field(default_factory=list)
    quality_checks:   list[str] = dc_field(default_factory=list)
    issues_risks:     list[str] = dc_field(default_factory=list)
    next_day_plan:    list[str] = dc_field(default_factory=list)
    incidents:        str = ""

    # ---- Diagnostics ----
    source_files: list[str] = dc_field(default_factory=list)
    conflicts:    list[dict] = dc_field(default_factory=list)
    notes:        list[str] = dc_field(default_factory=list)

    # ---- Reconciliation ----
    reconciliation: list[dict] = dc_field(default_factory=list)

    # ---- Project meta (company, contractor, consultant, logo, etc.) ----
    # Free-form dict, saved with the report in Turso, read by PDF export.
    project_meta: dict = dc_field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AggregatedReport":
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in data.items() if k in allowed})
