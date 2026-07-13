"""Aggregate scorecard across four layers.

Verdict bands per layer are mapped to A-F letter grades. Overall grade is
the worst grade across enabled layers — the whole point is that a single
weak layer disqualifies the server.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

BAND_TO_GRADE = {
    "GREEN": "A",
    "YELLOW": "B",
    "ORANGE": "D",
    "RED": "F",
}

GRADE_ORDER = ["A", "B", "C", "D", "F"]


@dataclass
class Scorecard:
    server_name: str | None
    tool_count: int
    layers: dict[str, dict[str, Any]] = field(default_factory=dict)
    overall_grade: str = "A"
    overall_band: str = "GREEN"

    def to_dict(self) -> dict[str, Any]:
        return {
            "server_name": self.server_name,
            "tool_count": self.tool_count,
            "overall_grade": self.overall_grade,
            "overall_band": self.overall_band,
            "layers": self.layers,
        }


def _worst(grades: list[str]) -> str:
    idx = 0
    for g in grades:
        idx = max(idx, GRADE_ORDER.index(g))
    return GRADE_ORDER[idx]


def _worst_band(bands: list[str]) -> str:
    order = ["GREEN", "YELLOW", "ORANGE", "RED"]
    idx = 0
    for b in bands:
        idx = max(idx, order.index(b))
    return order[idx]


def aggregate(
    server_name: str | None,
    tool_count: int,
    footprint: Any | None = None,
    scoping: Any | None = None,
    security: Any | None = None,
    name: Any | None = None,
) -> Scorecard:
    card = Scorecard(server_name=server_name, tool_count=tool_count)
    grades: list[str] = []
    bands: list[str] = []

    def register(key: str, obj: Any) -> None:
        if obj is None:
            return
        data = obj.to_dict()
        card.layers[key] = data
        grade = BAND_TO_GRADE.get(data.get("band", "GREEN"), "C")
        data["grade"] = grade
        grades.append(grade)
        bands.append(data.get("band", "GREEN"))

    register("footprint", footprint)
    register("scoping", scoping)
    register("security", security)
    register("name", name)

    card.overall_grade = _worst(grades) if grades else "A"
    card.overall_band = _worst_band(bands) if bands else "GREEN"
    return card
