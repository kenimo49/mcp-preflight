from pathlib import Path

from mcp_preflight.checks.scoping import check_scoping
from mcp_preflight.loader import load_server_spec

FIXTURE = Path(__file__).parent / "fixtures" / "sample_fastmcp.py"


def test_scoping_flags_when_to_use_present():
    spec = load_server_spec(FIXTURE)
    report = check_scoping(spec)
    findings_by_tool = {(f.tool, f.issue) for f in report.findings}
    assert not any(
        "when-to-use" in issue for _, issue in findings_by_tool
    ), findings_by_tool


def test_scoping_detects_vague_verb(tmp_path):
    fixture = tmp_path / "vague.py"
    fixture.write_text(
        'from mcp.server.fastmcp import FastMCP\n'
        'mcp = FastMCP("x")\n'
        '\n'
        '@mcp.tool()\n'
        'def do_stuff(arg: str) -> str:\n'
        '    """Handle the input somehow."""\n'
        '    return arg\n'
    )
    spec = load_server_spec(fixture)
    report = check_scoping(spec)
    issues = " ".join(f.issue for f in report.findings)
    assert "handle" in issues.lower()
