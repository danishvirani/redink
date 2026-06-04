"""Tests for the score aggregator, against the engine output on fixtures."""

from __future__ import annotations

from pathlib import Path

from redink.parser import parse_file
from redink.rules import run_all
from redink.score import score_session

FIXTURES = Path(__file__).parent / "fixtures" / "sessions"


def _score(name: str):
    return score_session(run_all(parse_file(FIXTURES / f"{name}.jsonl")))


def test_clean_scores_high():
    s = _score("clean")
    assert s.overall > 85
    assert s.total_firings == 0
    assert all(c.score == 100 for c in s.categories)
    assert s.cost_waste_usd == 0.0


def test_bloated_scores_low():
    s = _score("bloated")
    assert s.overall < 60
    assert s.total_firings == 4
    # the re-sent spec block shows up as a dollar figure
    assert s.cost_waste_usd > 0


def test_categories_are_named_and_ordered():
    s = _score("bloated")
    names = [c.name for c in s.categories]
    assert names == ["Context efficiency", "Prompt clarity", "Tool usage"]


def test_compacted_dings_context_efficiency():
    s = _score("compacted")
    ctx = next(c for c in s.categories if c.name == "Context efficiency")
    assert ctx.firings == 1
    assert ctx.score < 100
    assert s.overall < 100


def test_overall_never_negative():
    from redink.events import RuleFiring

    firings = [
        RuleFiring(i, "context_bloat", "error", "m", "s", {"repeated_tokens": 1000})
        for i in range(20)
    ]
    s = score_session(firings)
    assert s.overall == 0
