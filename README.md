# mcp-preflight

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub Sponsors](https://img.shields.io/github/sponsors/kenimo49?logo=githubsponsors&label=Sponsor)](https://github.com/sponsors/kenimo49)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-tip-FF5E5B?logo=kofi&logoColor=white)](https://ko-fi.com/kenimo49)

> ⚠️ **Status: v0.1 alpha — under active development.**
> Rules, thresholds, and scoring are being calibrated against real-world MCP servers.

Pre-flight checks for MCP (Model Context Protocol) servers.

`mcp-preflight` answers one question: **"Is this MCP server safe and efficient enough for LLMs to actually use?"** — before you publish it, install it, or let it into your agent config.

Existing MCP tools cover runtime security (MCP-Scan) and protocol compliance (MCP Inspector). This one covers the missing layer: **how expensive is the server just to keep registered, and are its tools scoped well enough for an LLM to pick the right one?**

Companion tool to the book **『MCP実践セキュリティ』** (Impress NextPublishing).

## The four layers

| Layer | What it measures | Status |
|-------|------------------|--------|
| **A. Passive Footprint** | Tokens the server steals from every LLM turn just by being listed. `tools/list` initial load, per-tool cost, bloat ratio, schema verbosity | v0.1 |
| **B. Use-Case Scoping** | Whether each tool is narrow enough that the LLM knows when to use it. When-to-use present, vague verb scan, overlap detection, naming consistency, AI Slop | v0.1 |
| **C. Security** | Own rules (prompt injection in description, tool shadowing, hardcoded secrets, transport hygiene) + optional MCP-Scan wrap | v0.1 own rules; wrap in v0.2 |
| **D. Name Safety** | Case collision, brand similarity, separator variants, namespace hygiene | v0.1 |

Design details: [docs/design.md](docs/design.md).

## Install

```bash
pip install mcp-preflight              # CLI + library
pip install "mcp-preflight[mcp]"       # + MCP server (stdio)
```

## Use as a CLI

```bash
# Full scan
mcp-preflight scan ./path/to/server.py
mcp-preflight scan http://localhost:8000/
mcp-preflight scan pypi:some-mcp

# Layer-only
mcp-preflight footprint ./server.py
mcp-preflight scoping ./server.py
mcp-preflight security ./server.py
mcp-preflight name my-new-mcp

# CI-friendly
mcp-preflight scan ./server.py --json
mcp-preflight scan ./server.py --format sarif
# exit codes: 0=GREEN/YELLOW, 1=ORANGE, 2=RED
```

## Use as an MCP server (self-hosting)

Register `mcp-preflight` itself as an MCP tool in Claude Code / Cursor / Windsurf, then ask the LLM to audit another MCP:

```json
{
  "mcpServers": {
    "mcp-preflight": {
      "command": "mcp-preflight-mcp"
    }
  }
}
```

Then in chat: *"score the MCP server at ./my-server.py"*.

## Why passive footprint matters

Every tool description and inputSchema in a registered MCP server is sent to the LLM on every turn — because the model needs to see them to decide which tool to call. A single verbose server can silently burn 5,000+ tokens per turn before anyone touches it.

`mcp-preflight footprint` measures exactly that, so you can trim before you publish.

## Roadmap

- **v0.1** — Layers A + B + D full, Layer C own rules, CLI + MCP server
- **v0.2** — MCP-Scan wrap, SARIF, real MCP client negotiation
- **v0.3** — Book『MCP実践セキュリティ』章別ルール取り込み
- **v0.4** — Registry-source targets (`github:` / `npm:`)

## Support this project

- 💚 [GitHub Sponsors](https://github.com/sponsors/kenimo49)
- ☕ [Ko-fi](https://ko-fi.com/kenimo49)

## License

MIT.
