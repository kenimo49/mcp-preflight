"""Layer A — Passive Footprint.

What the server costs on every LLM turn *just by being registered*. These
tokens are sent to the model on tools/list, before any tool is actually
invoked, so a fat MCP silently taxes every conversation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..loader import ServerSpec
from ..tokens import count_schema_tokens, count_tokens

TOTAL_GREEN = 1_500
TOTAL_YELLOW = 4_000
TOTAL_ORANGE = 8_000

PER_TOOL_BLOAT = 150
TOOL_COUNT_WARN = 15
TOOL_COUNT_FAIL = 30


@dataclass
class ToolFootprint:
    name: str
    description_tokens: int
    schema_tokens: int
    name_tokens: int

    @property
    def total(self) -> int:
        return self.description_tokens + self.schema_tokens + self.name_tokens


@dataclass
class FootprintReport:
    initial_token_load: int
    tool_count: int
    per_tool: list[ToolFootprint] = field(default_factory=list)
    bloated_tools: list[str] = field(default_factory=list)
    schema_heavy_tools: list[str] = field(default_factory=list)
    band: str = "GREEN"
    findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_token_load": self.initial_token_load,
            "tool_count": self.tool_count,
            "band": self.band,
            "findings": list(self.findings),
            "bloated_tools": list(self.bloated_tools),
            "schema_heavy_tools": list(self.schema_heavy_tools),
            "per_tool": [
                {
                    "name": t.name,
                    "description_tokens": t.description_tokens,
                    "schema_tokens": t.schema_tokens,
                    "name_tokens": t.name_tokens,
                    "total": t.total,
                }
                for t in self.per_tool
            ],
        }


def _band(total: int, tool_count: int) -> str:
    if tool_count > TOOL_COUNT_FAIL or total > TOTAL_ORANGE:
        return "RED"
    if total > TOTAL_YELLOW:
        return "ORANGE"
    if total > TOTAL_GREEN or tool_count > TOOL_COUNT_WARN:
        return "YELLOW"
    return "GREEN"


def check_footprint(spec: ServerSpec) -> FootprintReport:
    per_tool: list[ToolFootprint] = []
    total = 0
    for tool in spec.tools:
        dt = count_tokens(tool.description)
        st = count_schema_tokens(tool.input_schema)
        nt = count_tokens(tool.name)
        per_tool.append(
            ToolFootprint(
                name=tool.name,
                description_tokens=dt,
                schema_tokens=st,
                name_tokens=nt,
            )
        )
        total += dt + st + nt

    per_tool.sort(key=lambda t: t.total, reverse=True)
    bloated = [t.name for t in per_tool if t.description_tokens > PER_TOOL_BLOAT]
    schema_heavy = [
        t.name
        for t in per_tool
        if t.schema_tokens > max(80, t.description_tokens)
    ]

    findings: list[str] = []
    if len(spec.tools) > TOOL_COUNT_FAIL:
        findings.append(
            f"tool_count={len(spec.tools)} exceeds fail threshold {TOOL_COUNT_FAIL}"
        )
    elif len(spec.tools) > TOOL_COUNT_WARN:
        findings.append(
            f"tool_count={len(spec.tools)} exceeds warn threshold {TOOL_COUNT_WARN}"
        )
    if bloated:
        findings.append(
            f"{len(bloated)} tool(s) have description > {PER_TOOL_BLOAT} tokens: {', '.join(bloated[:5])}"
        )
    if schema_heavy:
        findings.append(
            f"{len(schema_heavy)} tool(s) have schema-heavy footprint: {', '.join(schema_heavy[:5])}"
        )
    if total > TOTAL_ORANGE:
        findings.append(
            f"initial_token_load={total} exceeds ORANGE ceiling {TOTAL_ORANGE}"
        )

    band = _band(total, len(spec.tools))
    return FootprintReport(
        initial_token_load=total,
        tool_count=len(spec.tools),
        per_tool=per_tool,
        bloated_tools=bloated,
        schema_heavy_tools=schema_heavy,
        band=band,
        findings=findings,
    )
