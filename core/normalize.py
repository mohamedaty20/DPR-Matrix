"""Deterministic normalization — the same input from different people
must collapse to the same key. Runs BEFORE merge."""
from __future__ import annotations
import re


# ---------------------------------------------------------------------------
# Buildings: "Building No 53", "B-53", "BLD 53", "53" → "53"
# ---------------------------------------------------------------------------
_BUILDING_PREFIX = re.compile(
    r"\b(building|bldg|bld|block|blk|tower|twr|no\.?|number|#)\b",
    re.IGNORECASE,
)


def norm_building(s: str) -> str:
    s = (s or "").strip()
    s = _BUILDING_PREFIX.sub(" ", s)
    s = re.sub(r"[^0-9A-Za-z]", "", s)
    s = s.lstrip("0") or "0"
    return s or "?"


# ---------------------------------------------------------------------------
# Floors: "2", "F2", "Floor No 2", "2nd floor", "Level 2" → "2"
# ---------------------------------------------------------------------------
_FLOOR_PREFIX = re.compile(r"\b(floor|flr|fl|level|lvl|f)\b\.?", re.IGNORECASE)
_ORDINAL = re.compile(r"(\d+)(st|nd|rd|th)\b", re.IGNORECASE)


def norm_floor(s: str) -> str:
    s = (s or "").strip()
    s = _ORDINAL.sub(r"\1", s)
    s = _FLOOR_PREFIX.sub(" ", s)
    m = re.search(r"\d+", s)
    if m:
        return m.group(0).lstrip("0") or "0"
    return s.strip() or "?"


# ---------------------------------------------------------------------------
# Activities: controlled vocabulary
# ---------------------------------------------------------------------------
_ACTIVITY_SYNONYMS: dict[str, str] = {
    "mortar":       "Mortar works",
    "mortaring":    "Mortar works",
    "masonry":      "Mortar works",
    "plaster":      "Plastering",
    "plastering":   "Plastering",
    "brick":        "Brickworks",
    "bricks":       "Brickworks",
    "brickwork":    "Brickworks",
    "brickworks":   "Brickworks",
    "bricklaying":  "Brickworks",
    "sealer":       "Sealer works",
    "sealing":      "Sealer works",
    "paint":        "Painting",
    "painting":     "Painting",
    "tile":         "Tiling",
    "tiling":       "Tiling",
    "steel":        "Steel fixing",
    "rebar":        "Steel fixing",
    "concrete":     "Concrete works",
    "concreting":   "Concrete works",
    "formwork":     "Formwork",
    "carpentry":    "Carpentry",
    "electric":     "Electrical",
    "electrical":   "Electrical",
    "plumbing":     "Plumbing",
    "excavation":   "Excavation",
    "backfilling":  "Backfilling",
    "waterproofing":"Waterproofing",
    "gypsum":       "Gypsum works",
    "ceiling":      "Ceiling works",
}


def norm_activity(s: str) -> str:
    raw = (s or "").strip()
    if not raw:
        return ""
    s = raw.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    compact = s.replace(" ", "")
    for key, canonical in _ACTIVITY_SYNONYMS.items():
        if key in compact:
            return canonical
    return raw.title()


# ---------------------------------------------------------------------------
# Numeric helpers
# ---------------------------------------------------------------------------
def to_float(v) -> float | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"-?\d+(?:\.\d+)?", str(v))
    return float(m.group(0)) if m else None


def fmt_num(n: float | None) -> str:
    if n is None:
        return ""
    return str(int(n)) if float(n).is_integer() else f"{n:g}"


def norm_unit(s: str) -> str:
    s = (s or "").strip().lower()
    mapping = {
        "m²": "m2", "m2": "m2", "sqm": "m2", "sq.m": "m2", "square meters": "m2",
        "m³": "m3", "m3": "m3", "cum": "m3", "cu.m": "m3", "cubic meters": "m3",
        "lm": "lm", "linear meters": "lm", "linear m": "lm",
        "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
        "ton": "t", "tons": "t", "t": "t",
        "bag": "bags", "bags": "bags",
        "nos": "nos", "no": "nos", "units": "nos", "unit": "nos", "pcs": "nos",
        "liter": "L", "liters": "L", "litre": "L", "litres": "L", "l": "L",
    }
    return mapping.get(s, s)
