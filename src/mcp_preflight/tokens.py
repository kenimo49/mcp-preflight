"""Token accounting.

Uses tiktoken's cl100k encoding by default (GPT-4 / Claude approximate). We
report tiktoken counts because they are stable and reproducible across
environments; real per-model counts differ but the relative ranking is what
Layer A cares about.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def _encoder():
    import tiktoken

    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(_encoder().encode(text))


def count_schema_tokens(schema: dict[str, Any]) -> int:
    return count_tokens(json.dumps(schema, ensure_ascii=False, sort_keys=True))
