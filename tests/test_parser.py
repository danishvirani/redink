"""Fixture-driven parser tests.

The fixtures (``tests/fixtures/sessions/*.jsonl``) are authored in real Claude
Code JSONL format by ``tests/fixtures/sessions/build.py``. See that script for
why they're synthetic rather than captured (NDA + no organic context-bloat in
real sessions). These tests pin parser behavior against that format.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from redink.errors import RedinkError
from redink.events import (
    FileEdit,
    ToolCall,
    TurnEnd,
    TurnStart,
    event_from_dict,
    event_to_dict,
)
from redink.parser import estimate_tokens, parse_events, parse_file

FIXTURES = Path(__file__).parent / "fixtures" / "sessions"


def _session(name: str):
    return parse_file(FIXTURES / f"{name}.jsonl")


# --- token heuristic -------------------------------------------------------


def test_estimate_tokens_is_quarter_length():
    assert estimate_tokens("a" * 400) == 100
    assert estimate_tokens("") == 0


# --- clean fixture ---------------------------------------------------------


def test_clean_parses_turns_and_prompts():
    s = _session("clean")
    assert s.session_id == "clean"
    assert len(s.turns) == 10
    # three genuine human prompts; tool-result carriers don't count
    assert len(s.user_prompts) == 3
    assert s.compaction_indices == []


def test_clean_distinguishes_tool_result_carriers_from_prompts():
    s = _session("clean")
    carriers = [t for t in s.turns if t.is_tool_result_only]
    assert carriers, "expected user messages carrying tool_result blocks"
    for t in carriers:
        assert not t.is_real_user_prompt


def test_clean_pairs_tool_use_with_response():
    s = _session("clean")
    calls = [c for t in s.turns for c in t.tool_calls]
    names = {c.tool for c in calls}
    assert {"Read", "Edit", "Write"} <= names
    read = next(c for c in calls if c.tool == "Read")
    assert read.response_summary  # tool_result text got paired back in
    assert read.response_token_count_est > 0


def test_clean_synthesizes_file_edits():
    s = _session("clean")
    edits = [e for t in s.turns for e in t.file_edits]
    paths = {e.path for e in edits}
    assert "src/tinylog/format.py" in paths
    assert "tests/test_format.py" in paths
    write_edit = next(e for e in edits if e.path == "tests/test_format.py")
    assert write_edit.lines_added > 0
    assert write_edit.lines_removed == 0


def test_clean_has_cost_from_usage():
    s = _session("clean")
    assert s.total_cost_usd > 0
    assistant_turns = [t for t in s.turns if t.role == "assistant"]
    assert all(t.total_tokens > 0 for t in assistant_turns)


# --- bloated fixture -------------------------------------------------------


def test_bloated_repeats_a_large_block_across_turns():
    s = _session("bloated")
    big = [t for t in s.turns if t.token_count_est > 2000]
    assert len(big) == 2, "the spec block should appear in two separate turns"
    # the shared payload is identical even though surrounding text differs
    marker = "tinylog line format specification"
    assert all(marker in t.text for t in big)


def test_bloated_has_a_vague_prompt_turn():
    s = _session("bloated")
    short = [t for t in s.user_prompts if len(t.text.split()) < 15]
    assert any("fix it" in t.text for t in short)


# --- compacted fixture -----------------------------------------------------


def test_compacted_detects_compaction_boundary():
    s = _session("compacted")
    assert s.compaction_indices == [4]
    comp = s.turns[4]
    assert comp.is_compaction
    assert comp.role == "system"


def test_compacted_references_symbol_across_boundary():
    s = _session("compacted")
    idx = s.compaction_indices[0]
    pre = " ".join(t.text for t in s.turns[:idx])
    post = " ".join(t.text for t in s.turns[idx + 1 :])
    assert "validate_schema" in pre
    assert "validate_schema" in post


# --- event stream / serialization -----------------------------------------


def test_event_stream_shape_and_ordering():
    events = parse_events(FIXTURES / "clean.jsonl")
    # every turn opens with TurnStart and closes with TurnEnd
    assert isinstance(events[0], TurnStart)
    assert isinstance(events[-1], TurnEnd)
    kinds = {type(e) for e in events}
    assert {TurnStart, TurnEnd, ToolCall, FileEdit} <= kinds


def test_every_event_round_trips_through_dict():
    for name in ("clean", "bloated", "compacted"):
        for e in parse_events(FIXTURES / f"{name}.jsonl"):
            assert event_from_dict(event_to_dict(e)) == e


# --- error handling --------------------------------------------------------


def test_missing_file_raises_redink_error():
    with pytest.raises(RedinkError, match="not found"):
        parse_file(FIXTURES / "does-not-exist.jsonl")


def test_malformed_json_raises_redink_error_with_excerpt(tmp_path: Path):
    bad = tmp_path / "bad.jsonl"
    bad.write_text('{"type":"user"}\nthis is not json\n')
    with pytest.raises(RedinkError, match="malformed JSON on line 2"):
        parse_file(bad)


def test_noise_lines_are_skipped(tmp_path: Path):
    noisy = tmp_path / "noisy.jsonl"
    noisy.write_text(
        "\n".join(
            [
                '{"type":"queue-operation","operation":"add"}',
                '{"type":"ai-title","aiTitle":"x"}',
                '{"type":"user","message":{"role":"user","content":"real prompt about src/a.py"}}',
                '{"type":"last-prompt","lastPrompt":"x"}',
            ]
        )
        + "\n"
    )
    s = parse_file(noisy)
    assert len(s.turns) == 1
    assert s.turns[0].is_real_user_prompt
