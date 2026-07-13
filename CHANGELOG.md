# Changelog

All notable changes to `mcp-scorecard` will be documented in this file.
The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.1.0] — 2026-07-13

### Changed
- Renamed from `mcp-preflight` to `mcp-scorecard` before first PyPI upload
  (an unrelated `mcp-preflight` project already occupies that PyPI namespace).
  Package, CLI, MCP server, and repository are all `mcp-scorecard` from v0.1.0.

### Added
- Four-layer scorecard model: Passive Footprint / Use-Case Scoping / Security / Name Safety.
- AST loader for FastMCP-style Python servers (`@mcp.tool()` extraction, no code execution).
- Manifest loader for non-Python MCP servers (`tools/list` JSON).
- Layer A — passive footprint: `initial_token_load` (tiktoken cl100k), `per_tool_tokens`,
  bloat detection (> 150 tok description), schema verbosity, tool count thresholds.
- Layer B — use-case scoping: when-to-use trigger detection, vague-verb scan,
  overlap detection, naming-style consistency, AI-slop markers.
- Layer C — security: prompt-injection-in-description, tool-shadowing, hardcoded
  secret regex sweep (AWS / GitHub / OpenAI / Anthropic / Slack / PEM).
- Layer D — name safety: case collision, Levenshtein brand similarity,
  separator variants, namespace hygiene. Bundled ~50 brands + known MCPs.
- CLI: `mcp-scorecard` / `mpf` with `scan`, `footprint`, `scoping`, `security`, `name`.
- MCP server: `mcp-scorecard-mcp` exposes five preflight_* tools over stdio.
- Dogfood/validation on domain-pre-flight, rag-db-advisor, opencut-mcp, and self.
- CI: pytest on 3.10 / 3.11 / 3.12, ruff.
- TypeScript static manifest extractor: `scripts/extract_ts_manifest.py`.
