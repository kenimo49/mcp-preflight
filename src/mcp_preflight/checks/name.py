"""Layer D — Name Safety.

Cheap, offline, deterministic checks against a bundled list of well-known
brands and known MCP servers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import Levenshtein

from ..data.known_brands import KNOWN_BRANDS, KNOWN_MCPS


@dataclass
class NameFinding:
    rule: str
    severity: str
    message: str


@dataclass
class NameReport:
    name: str
    findings: list[NameFinding] = field(default_factory=list)
    band: str = "GREEN"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "band": self.band,
            "findings": [
                {"rule": f.rule, "severity": f.severity, "message": f.message}
                for f in self.findings
            ],
        }


def _normalise(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _separator_variants(name: str) -> set[str]:
    parts = re.split(r"[-_ ]+", name.lower())
    if len(parts) < 2:
        return set()
    joined = "".join(parts)
    return {joined, "-".join(parts), "_".join(parts)} - {name.lower()}


def check_name(name: str) -> NameReport:
    report = NameReport(name=name)
    norm = _normalise(name)

    for brand in KNOWN_BRANDS:
        b_norm = _normalise(brand)
        if norm == b_norm and name != brand:
            report.findings.append(
                NameFinding(
                    "case_collision",
                    "high",
                    f"case-only variant of known brand '{brand}' — "
                    "attackers exploit exactly this",
                )
            )
        elif norm != b_norm and Levenshtein.distance(norm, b_norm) <= 2 and len(b_norm) >= 4:
            report.findings.append(
                NameFinding(
                    "brand_similarity",
                    "warn",
                    f"Levenshtein distance ≤ 2 to known brand '{brand}' — typosquat suspicion",
                )
            )

    for mcp in KNOWN_MCPS:
        m_norm = _normalise(mcp)
        if norm == m_norm and name != mcp:
            report.findings.append(
                NameFinding(
                    "mcp_case_collision",
                    "high",
                    f"case-only variant of known MCP '{mcp}'",
                )
            )
        elif norm != m_norm and Levenshtein.distance(norm, m_norm) <= 1 and len(m_norm) >= 4:
            report.findings.append(
                NameFinding(
                    "mcp_name_similarity",
                    "warn",
                    f"Levenshtein distance ≤ 1 to known MCP '{mcp}'",
                )
            )

    for variant in _separator_variants(name):
        for pool in (KNOWN_BRANDS, KNOWN_MCPS):
            if variant in pool:
                report.findings.append(
                    NameFinding(
                        "separator_variant_collision",
                        "warn",
                        f"separator variant '{variant}' is already a known name",
                    )
                )

    if not re.match(r"^[a-z][a-z0-9]*([-_/][a-z0-9]+)*$", name):
        report.findings.append(
            NameFinding(
                "namespace_hygiene",
                "info",
                "name uses mixed case or unusual characters; "
                "prefer kebab-case or @vendor/tool scoping",
            )
        )

    if any(f.severity == "high" for f in report.findings):
        report.band = "ORANGE"
    elif any(f.severity == "warn" for f in report.findings):
        report.band = "YELLOW"
    return report
