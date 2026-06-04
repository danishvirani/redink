"""Rule: reexplain_over_tool — describing a file the agent could just read.

Tool calls beat re-explaining. When a prompt names a file and then spends
paragraphs describing what's in it, that description is (a) token spend the
agent didn't need and (b) often stale or wrong. Letting the agent Read the file
is cheaper and more accurate. Fires info on prompts that name a path and
describe its contents at length.
"""

from __future__ import annotations

import re

from redink.events import RuleFiring
from redink.parser import Session
from redink.rules._text import PATH_RE
from redink.rules.config import RuleConfig

RULE_ID = "reexplain_over_tool"

# Markers that signal the prompt is *describing existing code*, not requesting
# new code. "add a helper that maps ..." should not trip; "contains a function
# which takes ..." should.
_DESCRIBES_RE = re.compile(
    r"\b(contains?|defines?|implements?|consists of|"
    r"which (takes|returns|maps|accepts|wraps|handles)|"
    r"it (also )?(has|defines|returns|wraps|imports))\b",
    re.I,
)


def run(session: Session, config: RuleConfig) -> list[RuleFiring]:
    firings: list[RuleFiring] = []
    for turn in session.user_prompts:
        if turn.token_count_est < config.reexplain_min_tokens:
            continue
        path_match = PATH_RE.search(turn.text)
        if not path_match or not _DESCRIBES_RE.search(turn.text):
            continue
        path = path_match.group(0)
        firings.append(
            RuleFiring(
                turn_id=turn.turn_id,
                rule_id=RULE_ID,
                severity="info",
                message=f"described the contents of {path} instead of letting the agent read it",
                suggestion=f"Let the agent read {path} instead of describing it.",
                metadata={"path": path, "described_tokens": turn.token_count_est},
            )
        )
    return firings
