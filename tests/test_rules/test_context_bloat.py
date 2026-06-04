"""Tests for the context_bloat rule."""

from __future__ import annotations

from pathlib import Path

from redink.parser import parse_file
from redink.rules import RuleConfig
from redink.rules import context_bloat

FIXTURES = Path(__file__).parents[1] / "fixtures" / "sessions"


def _run(name: str):
    return context_bloat.run(parse_file(FIXTURES / f"{name}.jsonl"), RuleConfig())


def test_fires_on_repasted_block():
    firings = _run("bloated")
    assert len(firings) == 1
    f = firings[0]
    assert f.rule_id == "context_bloat"
    assert f.severity == "error"  # the spec block is >2000 tokens
    assert f.metadata["repeated_tokens"] > 2000
    assert f.metadata["first_seen_turn"] == 1
    assert f.turn_id == 7  # the re-paste turn


def test_clean_session_does_not_fire():
    assert _run("clean") == []


def test_compacted_session_does_not_fire():
    assert _run("compacted") == []


def test_threshold_is_configurable():
    session = parse_file(FIXTURES / "bloated.jsonl")
    # raise the floor above the repeated block size -> nothing fires
    cfg = RuleConfig(context_bloat_min_tokens=100_000)
    assert context_bloat.run(session, cfg) == []
