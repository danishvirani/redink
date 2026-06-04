"""Tests for the brief_miss rule."""

from __future__ import annotations

from pathlib import Path

from redink.parser import parse_file
from redink.rules import brief_miss
from redink.rules.config import RuleConfig

FIXTURES = Path(__file__).parents[1] / "fixtures" / "sessions"


def _run(name: str):
    return brief_miss.run(parse_file(FIXTURES / f"{name}.jsonl"), RuleConfig())


def test_fires_on_long_cold_start_without_brief():
    firings = _run("bloated")
    assert len(firings) == 1
    f = firings[0]
    assert f.rule_id == "brief_miss"
    assert f.severity == "info"
    assert f.turn_id == 1
    assert f.metadata["opening_tokens"] > 100


def test_brief_bootstrap_suppresses_firing():
    # clean and compacted both open with a `tinylog brief` line
    assert _run("clean") == []
    assert _run("compacted") == []


def test_short_cold_start_does_not_fire(tmp_path: Path):
    import json

    p = tmp_path / "short.jsonl"
    p.write_text(
        json.dumps({"type": "user", "message": {"role": "user", "content": "hi there"}}) + "\n"
    )
    assert brief_miss.run(parse_file(p), RuleConfig()) == []
