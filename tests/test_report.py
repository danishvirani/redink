"""Tests for the ANSI terminal report renderer."""

from __future__ import annotations

from pathlib import Path

from redink.parser import parse_file
from redink.report import Palette, render, should_color
from redink.rules import run_all
from redink.score import score_session

FIXTURES = Path(__file__).parent / "fixtures" / "sessions"


def _render(name: str, color: bool = False) -> str:
    session = parse_file(FIXTURES / f"{name}.jsonl")
    score = score_session(run_all(session))
    return render(session, score, color=color)


def test_clean_report_shows_green_clean_line():
    out = _render("clean")
    assert "No anti-patterns detected" in out
    assert "Score  100/100" in out
    assert "Context efficiency" in out


def test_bloated_report_lists_each_firing_and_fix():
    out = _render("bloated")
    assert "Turn 7" in out
    assert "context_bloat" in out
    assert "✗" in out
    assert "→ " in out  # the fix-this line
    assert "What to do" in out
    assert "Score  56/100" in out


def test_compacted_report_mentions_the_symbol():
    out = _render("compacted")
    assert "compaction_loss" in out
    assert "validate_schema" in out


def test_no_color_has_no_escape_codes():
    out = _render("bloated", color=False)
    assert "\033[" not in out


def test_color_adds_escape_codes():
    out = _render("bloated", color=True)
    assert "\033[" in out


def test_palette_disabled_is_identity():
    p = Palette(enabled=False)
    assert p("red", "x") == "x"
    p2 = Palette(enabled=True)
    assert p2("red", "x") != "x"
    assert "x" in p2("red", "x")


def test_should_color_respects_no_color(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")

    class TTY:
        def isatty(self):
            return True

    assert should_color(TTY()) is False
