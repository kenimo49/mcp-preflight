"""CLI entry point."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.table import Table

from .checks.footprint import check_footprint
from .checks.name import check_name
from .checks.scoping import check_scoping
from .checks.score import aggregate
from .checks.security import check_security
from .loader import (
    load_server_spec,
    load_server_spec_from_directory,
    load_server_spec_from_manifest,
)

console = Console()


def _load(target: str):
    path = Path(target)
    if path.is_dir():
        return load_server_spec_from_directory(path)
    if path.suffix == ".json":
        return load_server_spec_from_manifest(path)
    return load_server_spec(path)


def _exit_code(band: str) -> int:
    return {"GREEN": 0, "YELLOW": 0, "ORANGE": 1, "RED": 2}.get(band, 1)


def _dump(data: dict[str, Any], as_json: bool) -> None:
    if as_json:
        console.print_json(data=data)


@click.group()
@click.version_option(package_name="mcp-scorecard")
def main() -> None:
    """Pre-flight checks for MCP servers."""


@main.command()
@click.argument("target")
@click.option("--json", "as_json", is_flag=True, help="Emit JSON instead of table.")
@click.option(
    "--layer",
    type=click.Choice(["footprint", "scoping", "security", "name", "all"]),
    default="all",
    help="Restrict to a specific layer.",
)
def scan(target: str, as_json: bool, layer: str) -> None:
    """Full scan of an MCP server (path to .py or dir containing one)."""
    spec = _load(target)

    footprint = check_footprint(spec) if layer in ("footprint", "all") else None
    scoping = check_scoping(spec) if layer in ("scoping", "all") else None
    security = check_security(spec) if layer in ("security", "all") else None
    name = (
        check_name(spec.server_name or spec.source_path.stem)
        if layer in ("name", "all")
        else None
    )

    card = aggregate(
        server_name=spec.server_name,
        tool_count=len(spec.tools),
        footprint=footprint,
        scoping=scoping,
        security=security,
        name=name,
    )

    if as_json:
        _dump(card.to_dict(), as_json=True)
    else:
        _render_scorecard(card)

    sys.exit(_exit_code(card.overall_band))


@main.command()
@click.argument("target")
@click.option("--json", "as_json", is_flag=True)
def footprint(target: str, as_json: bool) -> None:
    """Layer A only — passive token footprint."""
    spec = _load(target)
    report = check_footprint(spec)
    if as_json:
        _dump(report.to_dict(), True)
    else:
        _render_footprint(spec.server_name, report)
    sys.exit(_exit_code(report.band))


@main.command()
@click.argument("target")
@click.option("--json", "as_json", is_flag=True)
def scoping(target: str, as_json: bool) -> None:
    """Layer B only — use-case scoping."""
    spec = _load(target)
    report = check_scoping(spec)
    if as_json:
        _dump(report.to_dict(), True)
    else:
        _render_scoping(report)
    sys.exit(_exit_code(report.band))


@main.command()
@click.argument("target")
@click.option("--json", "as_json", is_flag=True)
def security(target: str, as_json: bool) -> None:
    """Layer C only — security own-rules."""
    spec = _load(target)
    report = check_security(spec)
    if as_json:
        _dump(report.to_dict(), True)
    else:
        _render_security(report)
    sys.exit(_exit_code(report.band))


@main.command()
@click.argument("name")
@click.option("--json", "as_json", is_flag=True)
def name(name: str, as_json: bool) -> None:
    """Layer D only — name safety for a proposed MCP name."""
    report = check_name(name)
    if as_json:
        _dump(report.to_dict(), True)
    else:
        _render_name(report)
    sys.exit(_exit_code(report.band))


def _render_scorecard(card) -> None:
    console.rule(f"[bold]mcp-scorecard[/bold] · {card.server_name or 'unnamed'}")
    console.print(
        f"Overall grade: [bold]{card.overall_grade}[/bold] "
        f"({card.overall_band}) · tools={card.tool_count}"
    )
    console.print()
    t = Table(show_header=True, header_style="bold")
    t.add_column("Layer")
    t.add_column("Band")
    t.add_column("Grade")
    t.add_column("Summary")
    for key, layer in card.layers.items():
        summary = _one_line_summary(key, layer)
        t.add_row(key, layer.get("band", ""), layer.get("grade", ""), summary)
    console.print(t)

    if "footprint" in card.layers:
        _render_footprint_details(card.layers["footprint"])

    for key, layer in card.layers.items():
        findings = layer.get("findings", [])
        if findings and key != "footprint":
            console.print(f"\n[bold]{key} findings[/bold]")
            for f in findings[:20]:
                console.print(f"  · {json.dumps(f, ensure_ascii=False)}")


def _one_line_summary(key: str, layer: dict[str, Any]) -> str:
    if key == "footprint":
        return f"{layer['initial_token_load']} tokens / {layer['tool_count']} tools"
    if key == "scoping":
        n = len(layer.get("findings", []))
        overlaps = len(layer.get("overlap_pairs", []))
        return f"{n} findings, {overlaps} overlap pair(s)"
    if key == "security":
        return f"{len(layer.get('findings', []))} findings"
    if key == "name":
        return f"{len(layer.get('findings', []))} findings"
    return ""


def _render_footprint(server_name: str | None, report) -> None:
    console.rule(f"footprint · {server_name or 'unnamed'}")
    console.print(
        f"initial_token_load = [bold]{report.initial_token_load}[/bold] "
        f"({report.band}) across {report.tool_count} tool(s)"
    )
    _render_footprint_details(report.to_dict())


def _render_footprint_details(data: dict[str, Any]) -> None:
    per_tool = data.get("per_tool", [])
    if not per_tool:
        return
    t = Table(title="per-tool footprint (top 10 by total)", show_header=True)
    t.add_column("Tool")
    t.add_column("Desc tok", justify="right")
    t.add_column("Schema tok", justify="right")
    t.add_column("Name tok", justify="right")
    t.add_column("Total", justify="right")
    for row in per_tool[:10]:
        t.add_row(
            row["name"],
            str(row["description_tokens"]),
            str(row["schema_tokens"]),
            str(row["name_tokens"]),
            str(row["total"]),
        )
    console.print(t)
    if data.get("findings"):
        console.print("[yellow]findings[/yellow]")
        for f in data["findings"]:
            console.print(f"  · {f}")


def _render_scoping(report) -> None:
    console.rule("scoping")
    console.print(f"band = {report.band}")
    console.print(f"naming_cases = {report.naming_cases}")
    for f in report.findings:
        console.print(f"[{f.severity}] {f.tool} — {f.issue}")
    for a, b, reason in report.overlap_pairs:
        console.print(f"[warn] overlap {a} <> {b}: {reason}")


def _render_security(report) -> None:
    console.rule("security")
    console.print(f"band = {report.band}")
    for f in report.findings:
        console.print(f"[{f.severity}] {f.rule} @ {f.tool or 'server'} — {f.message}")


def _render_name(report) -> None:
    console.rule(f"name · {report.name}")
    console.print(f"band = {report.band}")
    for f in report.findings:
        console.print(f"[{f.severity}] {f.rule} — {f.message}")


if __name__ == "__main__":
    main()
