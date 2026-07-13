"""Sample FastMCP server used as a loader fixture. Not executed."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("sample")


@mcp.tool()
def echo(message: str) -> str:
    """Send back the message verbatim.

    Use this when you need to confirm the server is reachable.
    """
    return message


@mcp.tool()
def add_numbers(a: int, b: int = 0) -> int:
    """Return a + b.

    Use this when you want to smoke-test integer arithmetic through MCP.
    """
    return a + b
