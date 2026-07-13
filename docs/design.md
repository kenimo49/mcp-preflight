# mcp-scorecard — design doc

> Pre-flight checks for MCP servers. Answers **"is this MCP server safe and efficient enough for LLMs to use?"** before you publish or install it.

## Positioning

Existing tools focus on runtime security (MCP-Scan / Cisco MCP-Scanner / AgentAuditKit) or protocol compliance (MCP Inspector / mcp-validator / mcp-validation). None cover the **LLM-facing quality** dimension: how much context the server consumes just by being listed, whether its tools have well-scoped use cases, and whether description prose is clear.

`mcp-scorecard` is the pre-publish scorecard that closes that gap, then wraps the security tools underneath so a single command grades your MCP end-to-end.

Companion to the book **『MCP実践セキュリティ』** — the book teaches the checks, this tool runs them.

## Four layers

### Layer A — Passive Footprint (differentiator, unique to this tool)

The tokens an MCP server steals from every LLM turn **just by being registered**, regardless of whether tools are called.

| Check | What it measures |
|-------|------------------|
| `initial_token_load` | Total tiktoken (cl100k) for the tools/list response: every tool name + description + inputSchema |
| `per_tool_tokens` | Token cost per tool, ranked highest → lowest |
| `bloat_ratio` | Fraction of tools whose description exceeds 150 tokens |
| `tool_count` | Total tool count. Warn > 15, fail > 30 |
| `schema_verbosity` | inputSchema tokens vs description tokens — schema-heavy tools are a common LLM budget sink |

Verdict bands: GREEN < 1,500 tokens · YELLOW 1,500–4,000 · ORANGE 4,000–8,000 · RED > 8,000 (numbers calibrated against real-world MCP servers, revised as we collect more data).

### Layer B — Use-Case Scoping (differentiator)

Whether each tool is narrow enough that the LLM knows when to reach for it. Broad "do-anything" tools inflate footprint and cause tool-selection errors.

| Check | Detects |
|-------|---------|
| `when_to_use_present` | Does the description state a trigger condition? (e.g. "Use this when …") |
| `vague_verb_scan` | `handle`, `process`, `manage`, `deal with`, `work with`, `execute` without qualifier |
| `overlap_detection` | Semantic near-duplicates between tools (same responsibility, different names) |
| `naming_consistency` | Mixed snake_case / camelCase / kebab-case across tools |
| `description_style` | AI Slop patterns (bullet-list-of-adjectives, marketing prose) — piggy-backs on avoid-ai-writing-en heuristics |
| `input_output_coherence` | Does the description promise what the schema returns? |

### Layer C — Security (borrow from existing tools + own rules)

Mostly borrowed. `mcp-scorecard security` shells out to MCP-Scan if installed and normalises the result, and adds a small independent ruleset for defence in depth.

Own rules:
- `prompt_injection_in_description` — imperative phrases aimed at the LLM inside tool descriptions ("ignore previous instructions", "always call …")
- `tool_shadowing` — names that impersonate common system utilities (`ls`, `read_file`, `execute`) without a namespace
- `hardcoded_secret_pattern` — regex sweep on the server source if `--source-path` given
- `transport_hygiene` — CORS, OAuth 2.1 presence for HTTP transports, DNS-rebinding headers
- `protocol_version` — reports negotiated MCP spec version, warns if pre-2025-06-18

External rules (via wrap):
- MCP-Scan / agent-scan detections (E001 prompt injection, E002 tool shadowing, W007/W008 credentials, W011 untrusted content, toxic flows)
- Optional: mcp-validation / mcp-validator for protocol compliance

### Layer D — Name Safety

Before publishing an MCP server, is the name safe from typosquat suspicion?

| Check | Method |
|-------|--------|
| `case_collision` | Same name in different casing already registered somewhere obvious (npm / PyPI / MCP.so) |
| `brand_similarity` | Levenshtein ≤ 2 to a bundled list of well-known brands / official MCP servers |
| `separator_variants` | `mcp-scan` vs `mcpscan` vs `mcp_scan` — flag if a common one is taken |
| `namespace_hygiene` | Recommend `@vendor/tool` style for scoped names |

Bundled list starts small (~50 obvious brands + known official MCPs) and grows via `scripts/refresh_known_brands.py`.

## Aggregate scorecard

A-F grade per layer, plus overall. JSON / Markdown / SARIF output. CI-friendly exit codes:
- `0` — GREEN / YELLOW
- `1` — ORANGE
- `2` — RED

```
Layer A (Footprint):     B  (2,340 tokens across 8 tools)
Layer B (Use-case):      C  (3 tools missing when-to-use)
Layer C (Security):      A  (no findings; MCP-Scan clean)
Layer D (Name safety):   A  (no collisions)
-----------------------------------------
Overall:                 B
```

## CLI shape

```
mcp-scorecard scan <target>              # all layers
mcp-scorecard footprint <target>         # Layer A only
mcp-scorecard scoping <target>           # Layer B only
mcp-scorecard security <target>          # Layer C only
mcp-scorecard name <name>                # Layer D only

# targets:
#   ./path/to/server.py       — Python entry (stdio, subprocess launch)
#   http://localhost:8000/    — HTTP transport
#   pypi:some-mcp             — install and scan
#   npm:@scope/some-mcp       — install and scan
#   github:owner/repo         — clone and scan
```

## MCP server surface (self-hosting / dogfooding)

Exposes the same layers as MCP tools so an LLM can audit an MCP server from a chat:

```
preflight_scan(target, layers?)
preflight_footprint(target)
preflight_scoping(target)
preflight_security(target)
preflight_name_check(name)
```

Runs via `mcp-scorecard-mcp` (stdio). Install as an MCP tool in Claude Code / Cursor and ask: *"score this MCP server"* → structured verdict.

## Validation targets (own dogfood set)

Phase 1 uses three real MCP servers written by the author to bootstrap the calibration:

1. **domain-pre-flight** (11 tools, mature) — reference for Layer A footprint norms
2. **rag-db-advisor** — smaller surface
3. **opencut-mcp** (v0.1.0) — brand-new MCP, expected clean baseline
4. **mcp-scorecard itself** — dogfooding, README badge

## Non-goals (v0.1)

- Runtime behaviour analysis / fuzzing
- Auto-fix
- Registry-wide scanning (crawling MCP.so etc.) — separate future project
- Payment / licensing checks

## Roadmap

- **v0.1** — Layer A + B full, Layer C own rules only, Layer D bundled list. CLI + MCP server.
- **v0.2** — MCP-Scan wrap, SARIF output, protocol negotiation via real client
- **v0.3** — Book『MCP実践セキュリティ』章別ルール取り込み
- **v0.4** — Registry-source scanning (github: / pypi: / npm: targets)
