"""Tests for the reexplain_over_tool rule."""

from __future__ import annotations

from pathlib import Path

from redink.parser import parse_file
from redink.rules import reexplain_over_tool
from redink.rules.config import RuleConfig

FIXTURES = Path(__file__).parents[1] / "fixtures" / "sessions"


def _run(name: str):
    return reexplain_over_tool.run(parse_file(FIXTURES / f"{name}.jsonl"), RuleConfig())


def test_fires_when_describing_a_named_file():
    firings = _run("bloated")
    assert len(firings) == 1
    f = firings[0]
    assert f.rule_id == "reexplain_over_tool"
    assert f.severity == "info"
    assert f.metadata["path"] == "src/tinylog/format.py"
    assert "read" in f.suggestion.lower()


def test_requesting_new_code_in_a_file_does_not_fire():
    # clean turn 1 names format.py but asks to ADD a helper, not describe it
    assert _run("clean") == []


def test_short_mentions_do_not_fire():
    assert _run("compacted") == []
