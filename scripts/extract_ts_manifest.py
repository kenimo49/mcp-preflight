"""Quick-and-dirty TypeScript tools/list extractor.

Reads a TS file containing a `ListToolsRequestSchema` handler with a static
tools literal and writes an mcp-preflight manifest JSON.

    python scripts/extract_ts_manifest.py path/to/index.ts \\
        --server-name opencut-mcp -o /tmp/opencut-mcp-manifest.json

Best-effort — handles the common `{ name: "...", description: "...", inputSchema: X }`
literal shape. Anything more dynamic needs a real TS AST parser (v0.2).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def extract(source: str) -> list[dict]:
    m = re.search(
        r"ListToolsRequestSchema[^{]*\{\s*tools:\s*\[(.*?)\],?\s*\}\s*\)\s*\)",
        source,
        re.S,
    )
    if not m:
        raise SystemExit("no ListToolsRequestSchema handler found")
    block = m.group(1)
    tools: list[dict] = []
    for tm in re.finditer(
        r'\{\s*name:\s*"([^"]+)"\s*,\s*description:\s*"([^"]+)"\s*,'
        r'\s*inputSchema:\s*\w+(?:\([^)]*\))?\s*\}',
        block,
    ):
        tools.append(
            {
                "name": tm.group(1),
                "description": tm.group(2),
                "inputSchema": {"type": "object", "properties": {}},
            }
        )
    return tools


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--server-name", default=None)
    ap.add_argument("-o", "--output", default="-")
    args = ap.parse_args()

    text = Path(args.source).read_text(encoding="utf-8")
    manifest = {"server_name": args.server_name, "tools": extract(text)}
    payload = json.dumps(manifest, ensure_ascii=False, indent=2)
    if args.output == "-":
        print(payload)
    else:
        Path(args.output).write_text(payload, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
