"""Shared text-analysis helpers for the rules.

Stdlib ``re`` only. These encode the heuristics the rules lean on: what counts
as an "anchor" (a file path or a code symbol), what counts as an
acknowledgment, and how to split a turn into comparable blocks. Heuristic by
design — see each rule's doc in ``docs/rules/`` for the imprecision tradeoffs.
"""

from __future__ import annotations

import re

# A file path with an extension: config.py, src/tinylog/format.py, tests/x.md
PATH_RE = re.compile(r"\b[\w./-]+\.[A-Za-z]{1,5}\b")

# snake_case (has at least one underscore) — validate_schema, render_line
_SNAKE_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b")
# CamelCase / internal-capital — ColorScheme, DEFAULT_SCHEME stays snake; ISO8601
_CAMEL_RE = re.compile(r"\b[A-Za-z]+[A-Z][A-Za-z0-9]*\b")

# Words that turn a short reply into an acknowledgment, not a real instruction.
_ACK_PHRASES = {
    "yes",
    "y",
    "ok",
    "okay",
    "yep",
    "yup",
    "sure",
    "ship it",
    "yes ship it",
    "lgtm",
    "thanks",
    "thank you",
    "go",
    "go ahead",
    "do it",
    "sounds good",
    "continue",
    "proceed",
    "perfect",
    "great",
    "nice",
    "cool",
    "done",
    "please do",
    "yes please",
    "approved",
}
_ACK_FIRST_WORDS = {"yes", "ok", "okay", "yep", "yup", "sure", "thanks", "lgtm", "perfect"}


def extract_paths(text: str) -> set[str]:
    return set(PATH_RE.findall(text))


def extract_symbols(text: str) -> set[str]:
    """Code-identifier-looking tokens: snake_case, CamelCase, and file paths."""
    syms: set[str] = set()
    syms.update(_SNAKE_RE.findall(text))
    syms.update(_CAMEL_RE.findall(text))
    syms.update(PATH_RE.findall(text))
    return syms


def has_anchor(text: str) -> bool:
    """True if the text names a file, a symbol, or a spec section."""
    if PATH_RE.search(text):
        return True
    if _SNAKE_RE.search(text) or _CAMEL_RE.search(text):
        return True
    if re.search(r"\b(section|step|phase|part)\s+\d+\b", text, re.I) or "§" in text:
        return True
    return False


def is_acknowledgment(text: str) -> bool:
    """True for short confirmations like 'yes', 'ship it', 'sounds good'."""
    norm = " ".join(re.sub(r"[^\w\s]", " ", text.lower()).split())
    if not norm:
        return False
    if norm in _ACK_PHRASES:
        return True
    words = norm.split()
    return len(words) <= 3 and words[0] in _ACK_FIRST_WORDS


def split_blocks(text: str) -> list[str]:
    """Split a turn into blank-line-separated blocks, stripped and non-empty."""
    return [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]


def normalize_block(block: str) -> str:
    """Whitespace-insensitive form for comparing 'same content' across turns."""
    return " ".join(block.split())
