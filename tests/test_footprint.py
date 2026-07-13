from pathlib import Path

from mcp_preflight.checks.footprint import check_footprint
from mcp_preflight.loader import load_server_spec

FIXTURE = Path(__file__).parent / "fixtures" / "sample_fastmcp.py"


def test_footprint_reports_per_tool_counts():
    spec = load_server_spec(FIXTURE)
    report = check_footprint(spec)
    assert report.tool_count == 2
    assert report.initial_token_load > 0
    assert {t.name for t in report.per_tool} == {"echo", "add_numbers"}
    assert report.band == "GREEN"
