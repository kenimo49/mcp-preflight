from pathlib import Path

from mcp_preflight.loader import (
    load_server_spec,
    load_server_spec_from_manifest,
)

FIXTURE = Path(__file__).parent / "fixtures" / "sample_fastmcp.py"


def test_ast_loader_extracts_tools():
    spec = load_server_spec(FIXTURE)
    assert spec.server_name == "sample"
    names = {t.name for t in spec.tools}
    assert names == {"echo", "add_numbers"}
    echo = next(t for t in spec.tools if t.name == "echo")
    assert "Send back" in echo.description
    assert echo.input_schema["required"] == ["message"]


def test_manifest_loader(tmp_path):
    p = tmp_path / "m.json"
    p.write_text(
        '{"server_name": "x", "tools": ['
        '{"name": "a", "description": "d", "inputSchema": {"type": "object"}}]}'
    )
    spec = load_server_spec_from_manifest(p)
    assert spec.server_name == "x"
    assert spec.tools[0].name == "a"
