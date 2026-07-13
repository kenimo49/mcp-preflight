"""mcp-preflight — pre-flight checks for MCP servers.

Four layers:
    A. Passive Footprint  — tokens consumed by tools/list alone
    B. Use-Case Scoping   — per-tool description quality
    C. Security           — own rules + optional MCP-Scan wrap
    D. Name Safety        — case collision, brand similarity
"""

__version__ = "0.1.0"
