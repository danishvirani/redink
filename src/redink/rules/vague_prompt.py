"""Rule: vague_prompt — a short prompt with nothing to anchor on.

"fix it", "make it better", "try again" — short, anchorless prompts get vague
output. The fix is anchoring (which file, which symbol, which section), not
retrying. Acknowledgments ("yes", "ship it") are short too but are not
instructions, so they're excluded.
"""

from __future__ import annotations

from redink.events import RuleFiring
from redink.parser import Session
from redink.rules._text import has_anchor, is_acknowledgment
from redink.rules.config import RuleConfig

RULE_ID = "vague_prompt"


def run(session: Session, config: RuleConfig) -> list[RuleFiring]:
    firings: list[RuleFiring] = []
    for turn in session.user_prompts:
        if len(turn.text.split()) >= config.vague_prompt_max_words:
            continue
        if has_anchor(turn.text):
            continue
        if is_acknowledgment(turn.text):
            continue
        firings.append(
            RuleFiring(
                turn_id=turn.turn_id,
                rule_id=RULE_ID,
                severity="warn",
                message=f'vague prompt with no anchor: "{turn.text.strip()[:60]}"',
                suggestion="Add an anchor: which file, which symbol, which section.",
                metadata={"word_count": len(turn.text.split())},
            )
        )
    return firings
