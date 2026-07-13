"""MCP server exposing mcp-preflight checks as tools.

Install with: pip install "mcp-preflight[mcp]"
Run via:      mcp-preflight-mcp
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "The MCP server requires the 'mcp' extra: pip install 'mcp-preflight[mcp]'"
    ) from e

from .checks.footprint import check_footprint
from .checks.name import check_name
from .checks.scoping import check_scoping
from .checks.score import aggregate
from .checks.security import check_security
from .loader import load_server_spec, load_server_spec_from_directory

mcp = FastMCP("mcp-preflight")


def _load(target: str):
    path = Path(target)
    if path.is_dir():
        return load_server_spec_from_directory(path)
    return load_server_spec(path)


@mcp.tool()
def preflight_scan(target: str) -> dict[str, Any]:
    """Run all four pre-flight layers on an MCP server and return a scorecard.

    Use this when you want a single overall grade for a Python-source MCP
    server before publishing or installing it. Provide the path to either the
    server .py file (e.g. `src/foo/mcp_server.py`) or a directory that
    contains one — the loader will find it.

    Returns overall_grade (A-F), overall_band (GREEN/YELLOW/ORANGE/RED),
    tool_count, and per-layer reports for footprint, scoping, security, name.
    """
    spec = _load(target)
    footprint = check_footprint(spec)
    scoping = check_scoping(spec)
    security = check_security(spec)
    name = check_name(spec.server_name or spec.source_path.stem)
    card = aggregate(
        server_name=spec.server_name,
        tool_count=len(spec.tools),
        footprint=footprint,
        scoping=scoping,
        security=security,
        name=name,
    )
    return card.to_dict()


@mcp.tool()
def preflight_footprint(target: str) -> dict[str, Any]:
    """Layer A — passive token footprint.

    Use this to measure exactly how many tokens the target MCP server steals
    from every LLM turn just by being registered (the tools/list response),
    before any tool is called. Reports initial_token_load, tool_count,
    per-tool token cost ranked highest-first, bloated tools (description
    > 150 tokens), and schema-heavy tools.
    """
    spec = _load(target)
    return check_footprint(spec).to_dict()


@mcp.tool()
def preflight_scoping(target: str) -> dict[str, Any]:
    """Layer B — use-case scoping quality.

    Use this to check whether each tool has a narrow enough purpose that the
    LLM can decide when to reach for it. Detects missing when-to-use hints,
    vague verbs (`handle`, `process`, `manage`, `execute`), naming-style
    inconsistency, tool-name overlap, AI-slop markers.
    """
    spec = _load(target)
    return check_scoping(spec).to_dict()


@mcp.tool()
def preflight_security(target: str) -> dict[str, Any]:
    """Layer C — security own-rules.

    Use this before installing an unknown MCP server. Own-rules scan for
    prompt-injection phrasing inside tool descriptions, tool-shadowing
    (names impersonating system utilities), and hardcoded secrets in the
    server source (AWS/GitHub/OpenAI/Anthropic/Slack keys, PEM private keys).
    In v0.2 this will also wrap MCP-Scan for defence in depth.
    """
    spec = _load(target)
    return check_security(spec).to_dict()


@mcp.tool()
def preflight_name_check(name: str) -> dict[str, Any]:
    """Layer D — pre-publish name safety.

    Use this BEFORE registering an MCP server name on PyPI/npm/MCP.so.
    Checks case-collision against known brands and known MCP servers,
    Levenshtein distance for typosquat suspicion, separator variants
    (e.g. `mcp-scan` vs `mcpscan`), and namespace hygiene.
    """
    return check_name(name).to_dict()


def run() -> None:
    """Console script entry point."""
    mcp.run()


if __name__ == "__main__":
    run()
