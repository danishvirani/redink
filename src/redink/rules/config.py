"""Tunable thresholds for the rule engine.

One dataclass, all defaults in one place. Each rule reads what it needs. Kept
separate from ``rules/__init__`` so individual rule modules can import it
without a circular import through the registry.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuleConfig:
    # context_bloat
    context_bloat_min_tokens: int = 500
    context_bloat_error_tokens: int = 2000
    # vague_prompt
    vague_prompt_max_words: int = 15
    # reexplain_over_tool
    reexplain_min_tokens: int = 50
    # brief_miss
    brief_miss_min_tokens: int = 100
