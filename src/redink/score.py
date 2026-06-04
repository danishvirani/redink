"""Aggregate rule firings into a summary score.

The opinion, quantified. Three categories — context efficiency, prompt clarity,
tool usage — each start at 100 and lose points per firing by severity. The
overall score subtracts *every* firing's penalty from 100, so it lands below
the category average: one clean category doesn't rescue a session full of
problems. This mirrors how a reviewer reads a PR — the worst issues set the
tone.

Penalties are deliberate, not calibrated against a corpus. v0.1 is about
flagging the egregious cases, not precision ranking. See docs/rules/.
"""

from __future__ import annotations

from dataclasses import dataclass

from redink.events import RuleFiring

# How much each severity costs.
_PENALTY = {"error": 18, "warn": 12, "info": 7}

# Which category each rule rolls up into.
_CATEGORY_OF_RULE = {
    "context_bloat": "Context efficiency",
    "compaction_loss": "Context efficiency",
    "vague_prompt": "Prompt clarity",
    "brief_miss": "Prompt clarity",
    "reexplain_over_tool": "Tool usage",
}
_CATEGORY_ORDER = ["Context efficiency", "Prompt clarity", "Tool usage"]

# Rough input price ($/token) for the "cost waste" estimate. Imprecise by
# design (ADR-001 — no tiktoken); enough to put a dollar figure on re-sent
# context.
_INPUT_PRICE_PER_TOKEN = 3.0 / 1_000_000


@dataclass(frozen=True)
class CategoryScore:
    name: str
    score: int
    firings: int


@dataclass(frozen=True)
class Score:
    overall: int
    categories: list[CategoryScore]
    total_firings: int
    cost_waste_usd: float
    firings: list[RuleFiring]


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def score_session(firings: list[RuleFiring]) -> Score:
    by_category: dict[str, list[RuleFiring]] = {name: [] for name in _CATEGORY_ORDER}
    for firing in firings:
        category = _CATEGORY_OF_RULE.get(firing.rule_id)
        if category is not None:
            by_category[category].append(firing)

    categories = [
        CategoryScore(
            name=name,
            score=_clamp(100 - sum(_PENALTY.get(f.severity, 0) for f in fired)),
            firings=len(fired),
        )
        for name, fired in ((n, by_category[n]) for n in _CATEGORY_ORDER)
    ]

    overall = _clamp(100 - sum(_PENALTY.get(f.severity, 0) for f in firings))

    repeated_tokens = sum(
        f.metadata.get("repeated_tokens", 0) for f in firings if f.rule_id == "context_bloat"
    )
    cost_waste = round(repeated_tokens * _INPUT_PRICE_PER_TOKEN, 4)

    return Score(
        overall=overall,
        categories=categories,
        total_firings=len(firings),
        cost_waste_usd=cost_waste,
        firings=firings,
    )
