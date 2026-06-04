"""Rule: context_bloat — content re-sent that was already in context.

The #1 token-waste anti-pattern: pasting a block of text (a spec, a file dump,
a CLAUDE.md) that the model already has from an earlier turn. Fires on the
*later* turn, pointing back at where the content first appeared.
"""

from __future__ import annotations

from redink.events import RuleFiring
from redink.parser import Session, estimate_tokens
from redink.rules._text import normalize_block, split_blocks
from redink.rules.config import RuleConfig

RULE_ID = "context_bloat"


def run(session: Session, config: RuleConfig) -> list[RuleFiring]:
    firings: list[RuleFiring] = []
    seen: dict[str, int] = {}  # normalized block -> turn it first appeared in

    for turn in session.turns:
        if turn.role != "user":
            continue
        for block in split_blocks(turn.text):
            tokens = estimate_tokens(block)
            if tokens < config.context_bloat_min_tokens:
                continue
            norm = normalize_block(block)
            first = seen.get(norm)
            if first is not None and first != turn.turn_id:
                severity = "error" if tokens >= config.context_bloat_error_tokens else "warn"
                firings.append(
                    RuleFiring(
                        turn_id=turn.turn_id,
                        rule_id=RULE_ID,
                        severity=severity,
                        message=(
                            f"re-sent {tokens:,} tokens already in context "
                            f"(first seen turn {first})"
                        ),
                        suggestion=(
                            f"This content was already in context at turn {first}. "
                            "Don't re-paste — the model still has it."
                        ),
                        metadata={"repeated_tokens": tokens, "first_seen_turn": first},
                    )
                )
            else:
                seen.setdefault(norm, turn.turn_id)
    return firings
