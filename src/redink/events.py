"""The shared event contract.

Every redink surface speaks this vocabulary. The parser (Track A) produces a
stream of these; the rule engine appends ``RuleFiring`` events; the terminal
report and the web UI / HTML export (Track B) consume them.

Stdlib only (ADR-001): frozen dataclasses + a hand-rolled dict (de)serializer.
The dict form carries a ``"kind"`` discriminator so a JSON consumer — SSE in the
browser, the embedded ``<script type="application/json">`` blob in the static
export — can round-trip an event without reflection.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

EventKind = Literal[
    "turn_start",
    "turn_content",
    "tool_call",
    "file_edit",
    "rule_firing",
    "turn_end",
]


@dataclass(frozen=True)
class TurnStart:
    turn_id: int
    role: Literal["user", "assistant", "system"]
    ts: str  # ISO8601


@dataclass(frozen=True)
class TurnContent:
    turn_id: int
    text: str
    token_count_est: int


@dataclass(frozen=True)
class ToolCall:
    turn_id: int
    tool: str
    args: dict
    response_summary: str  # truncated for display
    response_token_count_est: int


@dataclass(frozen=True)
class FileEdit:
    turn_id: int
    path: str
    diff: str  # unified diff format
    lines_added: int
    lines_removed: int


@dataclass(frozen=True)
class RuleFiring:
    turn_id: int
    rule_id: str  # e.g. "context_bloat"
    severity: Literal["info", "warn", "error"]
    message: str  # the callout text
    suggestion: str  # the "fix this" suggestion
    metadata: dict  # rule-specific extras (e.g. {"repeated_tokens": 8200})


@dataclass(frozen=True)
class TurnEnd:
    turn_id: int
    total_tokens: int
    cost_est_usd: float


Event = TurnStart | TurnContent | ToolCall | FileEdit | RuleFiring | TurnEnd


_KIND_BY_TYPE: dict[type, EventKind] = {
    TurnStart: "turn_start",
    TurnContent: "turn_content",
    ToolCall: "tool_call",
    FileEdit: "file_edit",
    RuleFiring: "rule_firing",
    TurnEnd: "turn_end",
}

_TYPE_BY_KIND: dict[str, type] = {kind: typ for typ, kind in _KIND_BY_TYPE.items()}


def event_kind(event: Event) -> EventKind:
    """Return the ``EventKind`` discriminator for an event instance."""
    return _KIND_BY_TYPE[type(event)]


def event_to_dict(event: Event) -> dict:
    """Serialize an event to a JSON-ready dict, tagged with its ``"kind"``.

    The tag is what lets ``event_from_dict`` (and any JS consumer) reconstruct
    the right shape without isinstance-sniffing.
    """
    data = asdict(event)
    data["kind"] = _KIND_BY_TYPE[type(event)]
    return data


def event_from_dict(data: dict) -> Event:
    """Reconstruct an event from its dict form. Inverse of ``event_to_dict``."""
    payload = dict(data)
    kind = payload.pop("kind", None)
    if kind is None:
        raise ValueError("event dict is missing its 'kind' discriminator")
    try:
        typ = _TYPE_BY_KIND[kind]
    except KeyError:
        raise ValueError(f"unknown event kind: {kind!r}") from None
    return typ(**payload)
