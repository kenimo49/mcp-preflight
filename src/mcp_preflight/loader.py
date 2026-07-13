"""Load MCP server tool specs from various targets.

v0.1 supports Python source files that follow the FastMCP convention:

    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("name")

    @mcp.tool()
    def some_tool(arg: str, opt: bool = False) -> dict:
        \"\"\"One-line summary.

        Longer description...
        \"\"\"
        ...

The loader walks the AST, finds every function decorated with `@<name>.tool(...)`,
and extracts:
    - name (from decorator kw `name=` or function name)
    - description (from decorator kw `description=` or docstring)
    - input_schema (derived from parameter annotations)

We do NOT execute the target — this keeps preflight safe to run on untrusted code.
"""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ToolSpec:
    """Extracted MCP tool spec."""

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    source_line: int | None = None

    @property
    def input_schema_json(self) -> str:
        return json.dumps(self.input_schema, ensure_ascii=False, sort_keys=True)


@dataclass
class ServerSpec:
    """Extracted MCP server spec (aggregate)."""

    source_path: Path
    server_name: str | None
    tools: list[ToolSpec] = field(default_factory=list)
    source_text: str = ""


_PY_TO_JSON: dict[str, str] = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list": "array",
    "dict": "object",
    "bytes": "string",
    "None": "null",
    "Any": "string",
}


def _annotation_to_schema(node: ast.expr | None) -> dict[str, Any]:
    """Best-effort ast.expr → JSON-schema fragment."""
    if node is None:
        return {"type": "string"}
    if isinstance(node, ast.Name):
        return {"type": _PY_TO_JSON.get(node.id, "string")}
    if isinstance(node, ast.Constant):
        return {"type": _PY_TO_JSON.get(type(node.value).__name__, "string")}
    if isinstance(node, ast.Subscript):
        base = node.value.id if isinstance(node.value, ast.Name) else ""
        if base in {"list", "List", "Sequence", "tuple", "Tuple"}:
            return {"type": "array"}
        if base in {"dict", "Dict", "Mapping"}:
            return {"type": "object"}
        if base in {"Optional", "Union"}:
            return _annotation_to_schema(node.slice)
        return {"type": "string"}
    if isinstance(node, ast.Attribute):
        return {"type": "string"}
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _annotation_to_schema(node.left)
    return {"type": "string"}


def _default_value(node: ast.expr | None) -> Any:
    if node is None:
        return None
    if isinstance(node, ast.Constant):
        return node.value
    return None


def _is_tool_decorator(dec: ast.expr) -> tuple[bool, dict[str, Any]]:
    """Return (is_tool_decorator, decorator_kwargs).

    Matches `@<any>.tool(...)` and `@tool(...)` — the FastMCP convention.
    """
    kwargs: dict[str, Any] = {}
    call: ast.Call | None = None
    if isinstance(dec, ast.Call):
        call = dec
        target = dec.func
    else:
        target = dec

    is_tool = False
    if isinstance(target, ast.Attribute) and target.attr == "tool":
        is_tool = True
    elif isinstance(target, ast.Name) and target.id == "tool":
        is_tool = True

    if call is not None and is_tool:
        for kw in call.keywords:
            if kw.arg in {"name", "description"} and isinstance(kw.value, ast.Constant):
                kwargs[kw.arg] = kw.value.value
    return is_tool, kwargs


def _server_name_from_ast(tree: ast.AST) -> str | None:
    """Extract the FastMCP server name from `FastMCP("...")` construction."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if isinstance(node.value, ast.Call):
                func = node.value.func
                is_fastmcp = (isinstance(func, ast.Name) and func.id == "FastMCP") or (
                    isinstance(func, ast.Attribute) and func.attr == "FastMCP"
                )
                if is_fastmcp and node.value.args:
                    first = node.value.args[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                        return first.value
    return None


def load_server_spec(source_path: str | Path) -> ServerSpec:
    """Parse a Python source file and extract every FastMCP-decorated tool."""
    path = Path(source_path)
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    server_name = _server_name_from_ast(tree)

    tools: list[ToolSpec] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        for dec in node.decorator_list:
            is_tool, kw = _is_tool_decorator(dec)
            if not is_tool:
                continue
            name = kw.get("name") or node.name
            description = kw.get("description") or (ast.get_docstring(node) or "")
            properties: dict[str, Any] = {}
            required: list[str] = []
            defaults = node.args.defaults
            args = node.args.args
            n_defaults = len(defaults)
            for i, arg in enumerate(args):
                if arg.arg in {"self", "cls", "ctx", "context"}:
                    continue
                schema = _annotation_to_schema(arg.annotation)
                default_idx = i - (len(args) - n_defaults)
                if default_idx >= 0:
                    schema["default"] = _default_value(defaults[default_idx])
                else:
                    required.append(arg.arg)
                properties[arg.arg] = schema
            input_schema: dict[str, Any] = {
                "type": "object",
                "properties": properties,
            }
            if required:
                input_schema["required"] = required
            tools.append(
                ToolSpec(
                    name=name,
                    description=description.strip(),
                    input_schema=input_schema,
                    source_line=node.lineno,
                )
            )
            break

    return ServerSpec(
        source_path=path,
        server_name=server_name,
        tools=tools,
        source_text=text,
    )


def load_server_spec_from_manifest(manifest_path: str | Path) -> ServerSpec:
    """Load from a JSON manifest matching the MCP `tools/list` response shape.

    Use this for non-Python MCP servers: dump their tools/list output to
    JSON and point mcp-preflight at it. Expected shape:

        {"tools": [{"name": "...", "description": "...", "inputSchema": {...}}]}

    Optionally the top-level object can carry a "server_name" key.
    """
    path = Path(manifest_path)
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    tools_data = data.get("tools", data if isinstance(data, list) else [])
    tools = [
        ToolSpec(
            name=t.get("name", ""),
            description=t.get("description", ""),
            input_schema=t.get("inputSchema", t.get("input_schema", {})),
        )
        for t in tools_data
    ]
    return ServerSpec(
        source_path=path,
        server_name=data.get("server_name") if isinstance(data, dict) else None,
        tools=tools,
        source_text=text,
    )


def load_server_spec_from_directory(root: str | Path) -> ServerSpec:
    """Locate the MCP server entry file in a directory (heuristic) and load it."""
    root = Path(root)
    candidates: list[Path] = []
    for name in ("mcp_server.py", "server.py", "__main__.py"):
        candidates.extend(root.rglob(name))
    candidates = [p for p in candidates if "test" not in p.parts and ".venv" not in p.parts]
    if not candidates:
        raise FileNotFoundError(f"No mcp_server.py / server.py found under {root}")
    # Prefer the one whose text mentions FastMCP.
    for c in candidates:
        if "FastMCP" in c.read_text(encoding="utf-8"):
            return load_server_spec(c)
    return load_server_spec(candidates[0])
