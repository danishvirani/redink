"""Rule: brief_miss — a long cold-start prompt with no brief bootstrap.

Brief-driven bootstrap beats a 500-word cold prompt. A `<tool> brief` line
injects project context in one line and keeps the opening turn small. When the
first real prompt is long and doesn't invoke a brief command, that's a missed
chance to start lean. Fires info, once, on the opening turn.
"""

from __future__ import annotations

import re

from redink.events import RuleFiring
from redink.parser import Session
from redink.rules.config import RuleConfig

RULE_ID = "brief_miss"

# A brief/bootstrap invocation in backticks: `tinylog brief`, `proj brief --x`
_BRIEF_RE = re.compile(r"`[^`]*\bbrief\b[^`]*`", re.I)


def run(session: Session, config: RuleConfig) -> list[RuleFiring]:
    prompts = session.user_prompts
    if not prompts:
        return []
    first = prompts[0]
    if first.token_count_est <= config.brief_miss_min_tokens:
        return []
    if _BRIEF_RE.search(first.text):
        return []
    return [
        RuleFiring(
            turn_id=first.turn_id,
            rule_id=RULE_ID,
            severity="info",
            message=(
                f"cold-started with a {first.token_count_est:,}-token prompt and no brief bootstrap"
            ),
            suggestion=(
                "Cold-start with `<your-brief-cmd> brief` to inject project context in one line."
            ),
            metadata={"opening_tokens": first.token_count_est},
        )
    ]
