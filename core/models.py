"""Canonical data contracts for DPR-Matrix."""
from __future__ import annotations
from dataclasses import dataclass, field as dc_field, asdict
from typing import Any


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------
@dataclass
class ExtractedDocument:
    filename: str
    mime: str
    sections: list[dict] = dc_field(default_factory=list)
    raw_text: str = ""
    meta: dict[str, Any] = dc_field(default_factory=dict)


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
@dataclass
class LineItem:
    label: str = ""
    quantity: str = ""
    unit: str = ""
    notes: str = ""
    sources: list[str] = dc_field(default_factory=list)
    count: int = 1

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Conflict:
    # NOTE: attribute is named `field` for JSON compatibility with the
    # prompt schema, so we import dataclasses.field as `dc_field`.
    field: str = ""
    values: list[str] = dc_field(default_factory=list)
    sources: list[str] = dc_field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AggregatedReport:
    project_name: str = ""
    report_date: str = ""
    site_location: str = ""
    prepared_by: str = ""
    weather: str = ""

    personnel_on_site: list[dict] = dc_field(default_factory=list)
    work_progress:     list[dict] = dc_field(default_factory=list)
    equipment:         list[dict] = dc_field(default_factory=list)
    materials:         list[dict] = dc_field(default_factory=list)

    hse_observations: list[str] = dc_field(default_factory=list)
    quality_checks:   list[str] = dc_field(default_factory=list)
    issues_risks:     list[str] = dc_field(default_factory=list)
    next_day_plan:    list[str] = dc_field(default_factory=list)

    incidents: str = ""

    source_files: list[str] = dc_field(default_factory=list)
    conflicts:    list[dict] = dc_field(default_factory=list)
    notes:        list[str] = dc_field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AggregatedReport":
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in data.items() if k in allowed})
