"""Replace lone UTF-16 surrogates in converter output so every later step can encode text.

Why: kordoc JSON output can carry a broken surrogate escape (U+DFB3); json.loads keeps it
as a lone surrogate and the first `.encode("utf-8")` (hash, file write, AI prompt) fails
(N2b: 2026-round-3-nw2, 대전대신중 2학기 2학년 계획, audit 268/934).
Rule: each lone surrogate becomes U+FFFD. Text without surrogates is returned unchanged
(same object), so existing hashes and AI caches stay valid.
Verify: pytest -q services/math-assessment-api/tests/test_n2b_surrogates.py
"""

from __future__ import annotations

import re

REPLACEMENT = "�"
LONE_SURROGATE_RE = re.compile("[\ud800-\udfff]")


def clean_text(value: str) -> str:
    """Return the text with lone surrogates replaced; unchanged text is returned as is."""
    if not LONE_SURROGATE_RE.search(value):
        return value
    return LONE_SURROGATE_RE.sub(REPLACEMENT, value)


def clean_tree(value):
    """Clean every string inside parsed JSON (dict keys and values, lists)."""
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, list):
        return [clean_tree(item) for item in value]
    if isinstance(value, dict):
        return {clean_tree(key): clean_tree(item) for key, item in value.items()}
    return value
