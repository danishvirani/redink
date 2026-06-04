"""Tests for the compaction_loss rule."""

from __future__ import annotations

from pathlib import Path

from redink.parser import parse_file
from redink.rules import compaction_loss
from redink.rules.config import RuleConfig

FIXTURES = Path(__file__).parents[1] / "fixtures" / "sessions"


def _run(name: str):
    return compaction_loss.run(parse_file(FIXTURES / f"{name}.jsonl"), RuleConfig())


def test_fires_on_symbol_reused_after_compaction():
    firings = _run("compacted")
    assert len(firings) == 1
    f = firings[0]
    assert f.rule_id == "compaction_loss"
    assert f.severity == "warn"
    assert f.metadata["symbol"] == "validate_schema"
    assert f.turn_id == 6  # the post-compaction turn that reuses it


def test_no_compaction_means_no_firing():
    assert _run("clean") == []
    assert _run("bloated") == []


def test_reread_after_compaction_suppresses_firing(tmp_path: Path):
    # Same shape as the fixture but with a Read of the symbol after compaction.
    import json

    def line(obj):
        return json.dumps(obj)

    rows = [
        {"type": "user", "message": {"role": "user", "content": "work on validate_schema"}},
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [{"type": "tool_use", "id": "t1", "name": "Read", "input": {}}],
            },
        },
        {"type": "system", "isMeta": True, "content": "", "compactMetadata": {"trigger": "auto"}},
        {
            "type": "assistant",
            "message": {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "t2",
                        "name": "Read",
                        "input": {"file_path": "validate_schema.py"},
                    }
                ],
            },
        },
        {"type": "user", "message": {"role": "user", "content": "now change validate_schema"}},
    ]
    p = tmp_path / "reread.jsonl"
    p.write_text("\n".join(line(r) for r in rows) + "\n")
    assert compaction_loss.run(parse_file(p), RuleConfig()) == []
