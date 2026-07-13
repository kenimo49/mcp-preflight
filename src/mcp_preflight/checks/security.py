"""Layer C — Security.

Independent ruleset for defence in depth. In v0.2 we shell out to MCP-Scan
and normalise its findings alongside these.

Own rules:
    - prompt_injection_in_description
    - tool_shadowing
    - hardcoded_secret_pattern (only if source scanned)
    - transport_hygiene (HTTP targets only, v0.2)
    - protocol_version (stdio negotiation, v0.2)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from ..loader import ServerSpec

PROMPT_INJECTION_PATTERNS = [
    re.compile(r"\bignore\s+(?:all\s+)?previous\b", re.I),
    re.compile(r"\bdisregard\s+(?:the|any)\s+instructions?\b", re.I),
    re.compile(r"\byou\s+must\s+(?:always|never)\b", re.I),
    re.compile(r"\balways\s+call\s+this\b", re.I),
    re.compile(r"\bsystem\s*[:：]\s*", re.I),
    re.compile(r"\brole\s*[:：]\s*system\b", re.I),
    re.compile(r"</?\s*(?:system|assistant|user)\s*>", re.I),
]

SHADOWED_NAMES = {
    "ls", "cat", "rm", "cp", "mv", "sudo", "curl", "wget",
    "read_file", "write_file", "delete_file", "list_files",
    "execute", "eval", "run_shell", "shell", "bash", "exec",
    "http_request", "fetch",
}

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aws_secret_key", re.compile(r"(?i)aws[_-]?secret[_-]?access[_-]?key\s*=\s*[\"'][^\"']{20,}[\"']")),
    ("github_token", re.compile(r"\bghp_[A-Za-z0-9]{30,}\b")),
    ("github_fine_grained", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9\-_]{20,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("private_key_pem", re.compile(r"-----BEGIN (?:RSA|EC|DSA|OPENSSH|PRIVATE) KEY-----")),
    (
        "hardcoded_bearer",
        re.compile(r"(?i)(?:authorization|bearer)\s*[:=]\s*[\"'][A-Za-z0-9._\-]{20,}[\"']"),
    ),
]


@dataclass
class SecurityFinding:
    rule: str
    tool: str | None
    severity: str  # info|warn|high|critical
    message: str
    line: int | None = None


@dataclass
class SecurityReport:
    findings: list[SecurityFinding] = field(default_factory=list)
    band: str = "GREEN"

    def to_dict(self) -> dict[str, Any]:
        return {
            "band": self.band,
            "findings": [
                {
                    "rule": f.rule,
                    "tool": f.tool,
                    "severity": f.severity,
                    "message": f.message,
                    "line": f.line,
                }
                for f in self.findings
            ],
        }


def _scan_prompt_injection(spec: ServerSpec) -> list[SecurityFinding]:
    out: list[SecurityFinding] = []
    for tool in spec.tools:
        for pat in PROMPT_INJECTION_PATTERNS:
            m = pat.search(tool.description or "")
            if m:
                out.append(
                    SecurityFinding(
                        rule="prompt_injection_in_description",
                        tool=tool.name,
                        severity="high",
                        message=f"prompt-injection-shaped phrase in description: '{m.group(0)}'",
                        line=tool.source_line,
                    )
                )
                break
    return out


def _scan_tool_shadowing(spec: ServerSpec) -> list[SecurityFinding]:
    out: list[SecurityFinding] = []
    for tool in spec.tools:
        base = tool.name.lower()
        if base in SHADOWED_NAMES:
            out.append(
                SecurityFinding(
                    rule="tool_shadowing",
                    tool=tool.name,
                    severity="warn",
                    message=(
                        f"tool name '{tool.name}' shadows a common system utility — "
                        "namespace it (e.g. 'myserver_ls')"
                    ),
                    line=tool.source_line,
                )
            )
    return out


def _scan_secrets(spec: ServerSpec) -> list[SecurityFinding]:
    out: list[SecurityFinding] = []
    text = spec.source_text or ""
    for rule, pat in SECRET_PATTERNS:
        for m in pat.finditer(text):
            line = text[: m.start()].count("\n") + 1
            out.append(
                SecurityFinding(
                    rule=f"hardcoded_secret:{rule}",
                    tool=None,
                    severity="critical",
                    message=f"potential hardcoded {rule} at line {line}",
                    line=line,
                )
            )
    return out


def check_security(spec: ServerSpec) -> SecurityReport:
    findings: list[SecurityFinding] = []
    findings.extend(_scan_prompt_injection(spec))
    findings.extend(_scan_tool_shadowing(spec))
    findings.extend(_scan_secrets(spec))

    band = "GREEN"
    if any(f.severity == "critical" for f in findings):
        band = "RED"
    elif any(f.severity == "high" for f in findings):
        band = "ORANGE"
    elif any(f.severity == "warn" for f in findings):
        band = "YELLOW"

    return SecurityReport(findings=findings, band=band)
