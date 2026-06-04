"""The redink rule engine.

Each rule is a module exposing ``RULE_ID`` and ``run(session, config) ->
list[RuleFiring]``. ``run_all`` fans out across every registered rule and
returns the firings sorted by turn. Add a rule by importing it and appending to
``ALL_RULES``.
"""

from __future__ import annotations

from redink.events import RuleFiring
from redink.parser import Session
from redink.rules import context_bloat
from redink.rules.config import RuleConfig

ALL_RULES = [
    context_bloat,
]


def run_all(session: Session, config: RuleConfig | None = None) -> list[RuleFiring]:
    config = config or RuleConfig()
    firings: list[RuleFiring] = []
    for rule in ALL_RULES:
        firings.extend(rule.run(session, config))
    firings.sort(key=lambda f: (f.turn_id, f.rule_id))
    return firings


__all__ = ["ALL_RULES", "RuleConfig", "run_all"]
