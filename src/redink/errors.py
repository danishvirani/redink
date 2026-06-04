"""redink's single exception type.

Per ADR-001 we don't get pydantic's friendly parse errors, so we funnel
malformed input through ``RedinkError`` with a short, quoted excerpt of the
offending text — enough to locate the problem without dumping a whole file.
"""

from __future__ import annotations


class RedinkError(Exception):
    """Any user-facing redink failure (bad session file, unreadable path, ...)."""

    @classmethod
    def from_input(cls, message: str, offending: str, limit: int = 300) -> "RedinkError":
        """Build an error that quotes the first ``limit`` chars of bad input."""
        excerpt = offending[:limit]
        if len(offending) > limit:
            excerpt += "…"
        return cls(f"{message}\n  → {excerpt!r}")
