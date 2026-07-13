"""Layer B — Use-Case Scoping.

Is each tool narrow enough that the LLM can figure out when to reach for it?
Broad "do-anything" tools inflate the footprint AND cause tool-selection
errors, so this layer runs alongside Layer A.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..loader import ServerSpec

WHEN_TO_USE_PATTERNS = [
    re.compile(r"\buse\s+(?:this|when|to)\b", re.I),
    re.compile(r"\bwhen\s+(?:you|the|to|user)\b", re.I),
    re.compile(r"\bfor\s+(?:when|cases|scenarios)\b", re.I),
    re.compile(r"\bcall\s+this\b", re.I),
    re.compile(r"\btrigger", re.I),
    re.compile(r"\bBEFORE\b"),
    re.compile(r"\bAfter\b"),
    re.compile(r"\b(?:呼び?出|使う|使用|使い)\b"),
]

VAGUE_VERBS = {
    "handle": "vague verb — specify the action (parse / validate / send)",
    "process": "vague verb — specify the action",
    "manage": "vague verb — specify the action",
    "deal with": "vague verb — specify the action",
    "work with": "vague verb — specify the action",
    "do": "vague verb — specify the action",
    "execute": "over-broad unless it really runs arbitrary code (which is a security concern)",
    "run": "vague verb — specify what runs",
    "perform": "vague verb — specify the action",
    "helper": "meta word — describe what it helps do",
    "utility": "meta word — describe what it helps do",
}

AI_SLOP_MARKERS = [
    re.compile(r"\bseamless(?:ly)?\b", re.I),
    re.compile(r"\brobust(?:ly)?\b", re.I),
    re.compile(r"\bleverag(?:e|ing|es)\b", re.I),
    re.compile(r"\bpowerful\b", re.I),
    re.compile(r"\bcomprehensive\b", re.I),
    re.compile(r"\bstate[- ]of[- ]the[- ]art\b", re.I),
    re.compile(r"\bcutting[- ]edge\b", re.I),
    re.compile(r"\benterprise[- ]grade\b", re.I),
]


def _detect_case(name: str) -> str:
    if "-" in name:
        return "kebab"
    if "_" in name:
        return "snake"
    if any(c.isupper() for c in name[1:]) and name[0].islower():
        return "camel"
    if name and name[0].isupper():
        return "pascal"
    return "flat"


@dataclass
class ToolScopingFinding:
    tool: str
    issue: str
    severity: str = "warn"


@dataclass
class ScopingReport:
    naming_cases: dict[str, list[str]] = field(default_factory=dict)
    findings: list[ToolScopingFinding] = field(default_factory=list)
    overlap_pairs: list[tuple[str, str, str]] = field(default_factory=list)
    band: str = "GREEN"

    def to_dict(self) -> dict[str, Any]:
        return {
            "band": self.band,
            "naming_cases": self.naming_cases,
            "findings": [
                {"tool": f.tool, "issue": f.issue, "severity": f.severity}
                for f in self.findings
            ],
            "overlap_pairs": [
                {"a": a, "b": b, "reason": reason} for a, b, reason in self.overlap_pairs
            ],
        }


def _stem_tokens(name: str) -> set[str]:
    parts = re.split(r"[_\-]+|(?<=[a-z])(?=[A-Z])", name)
    return {p.lower() for p in parts if len(p) > 2}


def _find_overlap(names: list[str]) -> list[tuple[str, str, str]]:
    pairs: list[tuple[str, str, str]] = []
    stems = {n: _stem_tokens(n) for n in names}
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            shared = stems[a] & stems[b]
            if len(shared) >= 2:
                pairs.append((a, b, f"shared stems: {sorted(shared)}"))
            elif shared and (a in b or b in a):
                pairs.append((a, b, f"one name contained in the other ({shared})"))
    return pairs


def check_scoping(spec: ServerSpec) -> ScopingReport:
    report = ScopingReport()

    cases: dict[str, list[str]] = {}
    for tool in spec.tools:
        c = _detect_case(tool.name)
        cases.setdefault(c, []).append(tool.name)
    report.naming_cases = cases

    for tool in spec.tools:
        desc = tool.description or ""

        if not desc.strip():
            report.findings.append(
                ToolScopingFinding(tool.name, "missing description", "fail")
            )
            continue

        if not any(p.search(desc) for p in WHEN_TO_USE_PATTERNS):
            report.findings.append(
                ToolScopingFinding(
                    tool.name,
                    "no explicit when-to-use trigger in description",
                    "warn",
                )
            )

        low = desc.lower()
        for verb, msg in VAGUE_VERBS.items():
            if re.search(rf"\b{re.escape(verb)}\b", low):
                report.findings.append(
                    ToolScopingFinding(tool.name, f"vague verb '{verb}': {msg}", "warn")
                )

        for pat in AI_SLOP_MARKERS:
            if pat.search(desc):
                report.findings.append(
                    ToolScopingFinding(
                        tool.name,
                        f"AI-slop marker '{pat.pattern}'",
                        "info",
                    )
                )
                break

        if len(desc) < 20:
            report.findings.append(
                ToolScopingFinding(
                    tool.name, "description under 20 chars — likely too terse", "warn"
                )
            )

    if len(cases) > 1:
        detail = ", ".join(f"{k}({len(v)})" for k, v in cases.items())
        report.findings.append(
            ToolScopingFinding("<server>", f"mixed naming styles: {detail}", "warn")
        )

    report.overlap_pairs = _find_overlap([t.name for t in spec.tools])

    fail = sum(1 for f in report.findings if f.severity == "fail")
    warn = sum(1 for f in report.findings if f.severity == "warn")
    if fail or len(report.overlap_pairs) > 3:
        report.band = "RED"
    elif warn >= max(3, len(spec.tools)):
        report.band = "ORANGE"
    elif warn >= 2 or report.overlap_pairs:
        report.band = "YELLOW"
    return report
