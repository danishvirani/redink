"""ANSI terminal renderer for ``redink audit``.

Per ADR-001 there's no ``rich`` — color is ~6 escape-code constants and a
palette that no-ops when output isn't a TTY (or ``NO_COLOR`` is set). The report
reads like a senior reviewer's margin notes: a red ✗ per anti-pattern with a
"fix this" line under it, a score block, and a deduped "what to do" tail. A
clean session gets a single green ✓.
"""

from __future__ import annotations

import os
import sys

from redink.parser import Session
from redink.score import Score

_SEVERITY_COLOR = {"error": "red", "warn": "red", "info": "yellow"}


class Palette:
    """ANSI escapes, or empty strings when color is disabled."""

    _CODES = {
        "red": "\033[31m",
        "yellow": "\033[33m",
        "green": "\033[32m",
        "dim": "\033[2m",
        "bold": "\033[1m",
        "reset": "\033[0m",
    }

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    def __call__(self, code: str, text: str) -> str:
        if not self.enabled:
            return text
        return f"{self._CODES[code]}{text}{self._CODES['reset']}"


def should_color(stream=sys.stdout) -> bool:
    if os.environ.get("NO_COLOR"):
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


def render(session: Session, score: Score, color: bool = False) -> str:
    p = Palette(color)
    lines: list[str] = []

    lines.append(
        p("bold", f"redink audit — session {session.session_id} ({len(session.turns)} turns)")
    )
    lines.append("")

    if not score.firings:
        lines.append("  " + p("green", "✓ No anti-patterns detected."))
    else:
        rule_width = max(len(f.rule_id) for f in score.firings)
        for firing in sorted(score.firings, key=lambda f: (f.turn_id, f.rule_id)):
            glyph = p(_SEVERITY_COLOR.get(firing.severity, "red"), "✗")
            turn = p("bold", f"Turn {firing.turn_id}")
            rule = p("dim", firing.rule_id.ljust(rule_width))
            lines.append(f"  {turn:<14} {glyph} {rule}  {firing.message}")
            lines.append("  " + p("dim", f"{'':14}   → {firing.suggestion}"))
        lines.append("")

    lines.extend(_score_block(score, p))

    suggestions = _deduped_suggestions(score)
    if suggestions:
        lines.append("")
        lines.append("  " + p("bold", "What to do"))
        for suggestion in suggestions:
            lines.append(f"    • {suggestion}")

    return "\n".join(lines) + "\n"


def _score_block(score: Score, p: Palette) -> list[str]:
    band = "green" if score.overall >= 85 else "yellow" if score.overall >= 60 else "red"
    lines = ["  " + p("bold", f"Score  {p(band, f'{score.overall}/100')}")]
    label_width = max(len(c.name) for c in score.categories)
    for cat in score.categories:
        lines.append(f"    {cat.name.ljust(label_width)}   {cat.score}")
    lines.append(f"    {'Anti-patterns'.ljust(label_width)}   {score.total_firings} flagged")
    lines.append(
        f"    {'Cost waste (est.)'.ljust(label_width)}   ${score.cost_waste_usd:.2f} / session"
    )
    return lines


def _deduped_suggestions(score: Score) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for firing in sorted(score.firings, key=lambda f: (f.turn_id, f.rule_id)):
        if firing.suggestion not in seen:
            seen.add(firing.suggestion)
            ordered.append(firing.suggestion)
    return ordered
