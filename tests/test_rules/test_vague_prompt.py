"""Tests for the vague_prompt rule."""

from __future__ import annotations

from pathlib import Path

from redink.parser import parse_file
from redink.rules import vague_prompt
from redink.rules.config import RuleConfig

FIXTURES = Path(__file__).parents[1] / "fixtures" / "sessions"


def _run(name: str):
    return vague_prompt.run(parse_file(FIXTURES / f"{name}.jsonl"), RuleConfig())


def test_fires_on_anchorless_short_prompt():
    firings = _run("bloated")
    assert len(firings) == 1
    f = firings[0]
    assert f.rule_id == "vague_prompt"
    assert f.severity == "warn"
    assert "just fix it" in f.message


def test_anchored_prompts_do_not_fire():
    # clean session prompts all name a file or symbol, or are acknowledgments
    assert _run("clean") == []


def test_acknowledgments_are_not_vague():
    from redink.rules._text import is_acknowledgment

    assert is_acknowledgment("yes, ship it")
    assert is_acknowledgment("sounds good")
    assert not is_acknowledgment("just fix it")
