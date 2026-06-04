"""Rule: compaction_loss — a reference dropped by compaction, used anyway.

When Claude Code compacts, it summarizes earlier context and discards the
detail. If a symbol or file that was loaded *before* compaction gets referenced
*after* it — without being re-read via a tool call — the model is likely
working from a lossy summary. Fires on the post-compaction turn that reuses the
stale reference.
"""

from __future__ import annotations

from redink.events import RuleFiring
from redink.parser import Session
from redink.rules._text import extract_symbols
from redink.rules.config import RuleConfig

RULE_ID = "compaction_loss"
_READ_TOOLS = {"Read", "Grep", "Glob"}


def run(session: Session, config: RuleConfig) -> list[RuleFiring]:
    indices = session.compaction_indices
    if not indices:
        return []

    firings: list[RuleFiring] = []
    fired: set[str] = set()  # symbols already flagged, across all boundaries

    for c in indices:
        pre_symbols = _symbols_before(session, c)
        reloaded = _symbols_reloaded_after(session, c)
        compaction_turn_id = session.turns[c].turn_id

        for turn in session.turns[c + 1 :]:
            if turn.is_compaction:
                continue
            for symbol in extract_symbols(turn.text) & pre_symbols:
                if symbol in reloaded or symbol in fired:
                    continue
                fired.add(symbol)
                firings.append(
                    RuleFiring(
                        turn_id=turn.turn_id,
                        rule_id=RULE_ID,
                        severity="warn",
                        message=(
                            f"reference to '{symbol}' may have been lost in compaction "
                            f"(last loaded before turn {compaction_turn_id})"
                        ),
                        suggestion=(
                            f"Reference to '{symbol}' may have been lost in compaction. "
                            "Read it explicitly before relying on it."
                        ),
                        metadata={"symbol": symbol, "compaction_turn": compaction_turn_id},
                    )
                )
    return firings


def _symbols_before(session: Session, c: int) -> set[str]:
    symbols: set[str] = set()
    for turn in session.turns[:c]:
        symbols |= extract_symbols(turn.text)
        for call in turn.tool_calls:
            symbols |= extract_symbols(call.response_summary)
            symbols |= extract_symbols(" ".join(str(v) for v in call.args.values()))
    return symbols


def _symbols_reloaded_after(session: Session, c: int) -> set[str]:
    reloaded: set[str] = set()
    for turn in session.turns[c + 1 :]:
        for call in turn.tool_calls:
            if call.tool not in _READ_TOOLS:
                continue
            reloaded |= extract_symbols(" ".join(str(v) for v in call.args.values()))
            reloaded |= extract_symbols(call.response_summary)
    return reloaded
