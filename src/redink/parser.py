"""Claude Code JSONL session parser.

Reads a ``~/.claude/projects/<project>/<id>.jsonl`` file and produces:

* a flat ``list[Event]`` (the shared contract — what Track B streams over SSE
  and embeds in the static export), and
* a richer ``Session`` model (turns grouped with their tool calls, file edits,
  usage and compaction boundaries) — what the rule engine consumes.

Both come out of one pass so the two surfaces never disagree about what
happened in a session.

Token counts use the ADR-001 heuristic (``len(text) // 4``); see
``docs/rules/context-bloat.md`` for the imprecision note. Per-turn cost uses
the real ``usage`` block when present, falling back to the heuristic.
"""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass, field
from pathlib import Path

from redink.errors import RedinkError
from redink.events import (
    Event,
    FileEdit,
    ToolCall,
    TurnContent,
    TurnEnd,
    TurnStart,
)

CHARS_PER_TOKEN = 4
RESPONSE_SUMMARY_LIMIT = 500

# Top-level line types that are not conversation turns — bookkeeping noise.
_NOISE_TYPES = {"queue-operation", "attachment", "ai-title", "last-prompt", "summary"}

# Tool names that mutate files, used to synthesize FileEdit events.
_EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

# Rough per-1M-token prices (USD) by model-name substring. Estimates only —
# documented as imprecise; we never bill on these.
_PRICES: dict[str, tuple[float, float]] = {
    "opus": (15.0, 75.0),
    "sonnet": (3.0, 15.0),
    "haiku": (0.80, 4.0),
}


def estimate_tokens(text: str) -> int:
    """ADR-001 heuristic: ~4 chars per token for code-mixed English."""
    return len(text) // CHARS_PER_TOKEN


def _price_for(model: str) -> tuple[float, float]:
    name = (model or "").lower()
    for key, prices in _PRICES.items():
        if key in name:
            return prices
    return _PRICES["sonnet"]  # sensible default


@dataclass
class Turn:
    """One conversation turn, enriched for the rule engine.

    Not part of the wire contract — that's ``events.py``. This is the in-memory
    model rules pattern-match against.
    """

    turn_id: int
    role: str  # "user" | "assistant" | "system"
    ts: str
    text: str
    token_count_est: int
    tool_calls: list[ToolCall] = field(default_factory=list)
    file_edits: list[FileEdit] = field(default_factory=list)
    is_compaction: bool = False
    is_tool_result_only: bool = False  # user msg carrying only tool_result blocks
    total_tokens: int = 0
    cost_est_usd: float = 0.0

    @property
    def is_real_user_prompt(self) -> bool:
        """A genuine human prompt — not a tool-result carrier, not empty."""
        return self.role == "user" and not self.is_tool_result_only and bool(self.text.strip())


@dataclass
class Session:
    """A parsed session: turns + the flat event stream + convenience accessors."""

    session_id: str
    turns: list[Turn]
    events: list[Event]

    @property
    def compaction_indices(self) -> list[int]:
        """Positions in ``turns`` where compaction occurred."""
        return [i for i, t in enumerate(self.turns) if t.is_compaction]

    @property
    def user_prompts(self) -> list[Turn]:
        return [t for t in self.turns if t.is_real_user_prompt]

    @property
    def total_cost_usd(self) -> float:
        return round(sum(t.cost_est_usd for t in self.turns), 4)


def _flatten_text(content: object) -> str:
    """Visible assistant/user text — text blocks only (no thinking/tool blocks)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                txt = block.get("text")
                if isinstance(txt, str):
                    parts.append(txt)
        return "\n".join(parts)
    return ""


def _tool_result_text(content: object) -> str:
    """Tool-result content can be a str or a list of text/image blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\n".join(parts)
    return ""


def _unified_diff(path: str, old: str, new: str) -> tuple[str, int, int]:
    old_lines = old.splitlines()
    new_lines = new.splitlines()
    diff = list(difflib.unified_diff(old_lines, new_lines, fromfile=path, tofile=path, lineterm=""))
    added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
    return "\n".join(diff), added, removed


def _file_edits(turn_id: int, name: str, inp: dict) -> list[FileEdit]:
    path = inp.get("file_path") or inp.get("notebook_path") or inp.get("path") or ""
    if name == "Write":
        content = inp.get("content") or inp.get("contents") or ""
        added = content.splitlines()
        diff = "\n".join("+" + line for line in added)
        return [FileEdit(turn_id, path, diff, len(added), 0)]
    if name == "Edit":
        diff, added, removed = _unified_diff(
            path, inp.get("old_string", ""), inp.get("new_string", "")
        )
        return [FileEdit(turn_id, path, diff, added, removed)]
    if name == "MultiEdit":
        diff_parts: list[str] = []
        total_added = total_removed = 0
        for edit in inp.get("edits", []):
            if not isinstance(edit, dict):
                continue
            d, a, r = _unified_diff(path, edit.get("old_string", ""), edit.get("new_string", ""))
            diff_parts.append(d)
            total_added += a
            total_removed += r
        return [FileEdit(turn_id, path, "\n".join(diff_parts), total_added, total_removed)]
    if name == "NotebookEdit":
        new = inp.get("new_source", "")
        added = new.splitlines()
        diff = "\n".join("+" + line for line in added)
        return [FileEdit(turn_id, path, diff, len(added), 0)]
    return []


def _turn_cost(usage: dict | None, model: str) -> tuple[int, float]:
    if not usage:
        return 0, 0.0
    inp = usage.get("input_tokens") or 0
    out = usage.get("output_tokens") or 0
    cache_read = usage.get("cache_read_input_tokens") or 0
    cache_create = usage.get("cache_creation_input_tokens") or 0
    price_in, price_out = _price_for(model)
    cost = (
        inp * price_in
        + out * price_out
        + cache_read * price_in * 0.1  # cached reads are ~10% of input price
        + cache_create * price_in * 1.25  # cache writes carry a premium
    ) / 1_000_000
    total = inp + out + cache_read + cache_create
    return total, round(cost, 6)


def _read_lines(path: Path) -> list[dict]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RedinkError(f"could not read session file: {path}\n  → {exc}") from exc
    objects: list[dict] = []
    for lineno, line in enumerate(raw.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RedinkError.from_input(
                f"malformed JSON on line {lineno} of {path.name}", line
            ) from exc
        if isinstance(obj, dict):
            objects.append(obj)
    return objects


def _collect_tool_results(objects: list[dict]) -> dict[str, str]:
    """Map tool_use_id -> response text, scanning every user message once."""
    results: dict[str, str] = {}
    for obj in objects:
        message = obj.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                tid = block.get("tool_use_id")
                if isinstance(tid, str):
                    results[tid] = _tool_result_text(block.get("content"))
    return results


def _is_compaction(obj: dict) -> bool:
    return bool(obj.get("compactMetadata") or obj.get("isCompactSummary"))


def parse_file(path: str | Path) -> Session:
    """Parse a Claude Code session file into a :class:`Session`."""
    path = Path(path)
    if not path.exists():
        raise RedinkError(f"session file not found: {path}")

    objects = _read_lines(path)
    tool_results = _collect_tool_results(objects)

    session_id = path.stem
    turns: list[Turn] = []
    events: list[Event] = []
    next_id = 1

    for obj in objects:
        compaction = _is_compaction(obj)
        line_type = obj.get("type")
        if not compaction and line_type in _NOISE_TYPES:
            continue

        message = obj.get("message")
        if compaction:
            role = "system"
            content: object = obj.get("content") or (
                message.get("content") if isinstance(message, dict) else ""
            )
            text = _flatten_text(content) if content else "context compacted"
        elif isinstance(message, dict) and line_type in ("user", "assistant"):
            role = message.get("role") or line_type
            content = message.get("content")
            text = _flatten_text(content)
        else:
            continue

        turn = _build_turn(next_id, role, obj, message, content, text, tool_results, compaction)
        turns.append(turn)
        _emit_turn_events(events, turn)
        next_id += 1

    return Session(session_id=session_id, turns=turns, events=events)


def _build_turn(
    turn_id: int,
    role: str,
    obj: dict,
    message: object,
    content: object,
    text: str,
    tool_results: dict[str, str],
    compaction: bool,
) -> Turn:
    ts = obj.get("timestamp") or ""
    tool_calls: list[ToolCall] = []
    file_edits: list[FileEdit] = []
    is_tool_result_only = False

    if isinstance(content, list):
        block_types = {b.get("type") for b in content if isinstance(b, dict)}
        is_tool_result_only = "tool_result" in block_types and "text" not in block_types
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = block.get("name") or ""
            inp = block.get("input") if isinstance(block.get("input"), dict) else {}
            response = tool_results.get(block.get("id", ""), "")
            summary = response[:RESPONSE_SUMMARY_LIMIT]
            tool_calls.append(
                ToolCall(
                    turn_id=turn_id,
                    tool=name,
                    args=inp,
                    response_summary=summary,
                    response_token_count_est=estimate_tokens(response),
                )
            )
            if name in _EDIT_TOOLS:
                file_edits.extend(_file_edits(turn_id, name, inp))

    model = message.get("model", "") if isinstance(message, dict) else ""
    usage = message.get("usage") if isinstance(message, dict) else None
    total_tokens, cost = _turn_cost(usage if isinstance(usage, dict) else None, model)
    token_est = estimate_tokens(text)
    if total_tokens == 0:
        total_tokens = token_est

    return Turn(
        turn_id=turn_id,
        role=role,
        ts=ts,
        text=text,
        token_count_est=token_est,
        tool_calls=tool_calls,
        file_edits=file_edits,
        is_compaction=compaction,
        is_tool_result_only=is_tool_result_only,
        total_tokens=total_tokens,
        cost_est_usd=cost,
    )


def _emit_turn_events(events: list[Event], turn: Turn) -> None:
    events.append(TurnStart(turn_id=turn.turn_id, role=turn.role, ts=turn.ts))
    if turn.text.strip():
        events.append(
            TurnContent(
                turn_id=turn.turn_id,
                text=turn.text,
                token_count_est=turn.token_count_est,
            )
        )
    events.extend(turn.tool_calls)
    events.extend(turn.file_edits)
    events.append(
        TurnEnd(
            turn_id=turn.turn_id,
            total_tokens=turn.total_tokens,
            cost_est_usd=turn.cost_est_usd,
        )
    )


def parse_events(path: str | Path) -> list[Event]:
    """Convenience for Track B: just the flat event stream."""
    return parse_file(path).events
