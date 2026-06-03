# Track A — redink engine (parser + rules + CLI audit)

This is a self-contained brief for a fresh Claude Code session working on Track A of redink v0.1. The other track (Track B — the live web UI) is being built in parallel by another Claude Code session against the same repo. **Stay in your lane** so we can merge cleanly.

---

## Read these first (in order)

1. `README.md` — what redink is, the demo, the opinion
2. `docs/strategy.md` — why this product, what the brand is
3. `docs/roadmap.md` — the v0.0 → v0.3 build sequence + the parallel-track split
4. `docs/decisions/ADR-001-stdlib-only.md` — the non-negotiable: no runtime deps

Then `cat docs/sessions/track-a-engine.md` (this file) and proceed.

---

## What Track A owns

Everything that turns a Claude Code session log into a stream of typed events + scored rule firings:

- `src/redink/events.py` — the shared event types (see contract below)
- `src/redink/parser.py` — JSONL → typed events
- `src/redink/rules/` — one module per rule (context_bloat, compaction_loss, vague_prompt, reexplain_over_tool, brief_miss)
- `src/redink/score.py` — aggregate per-rule firings into the summary score block
- `src/redink/report.py` — ANSI terminal renderer for `redink audit`
- `src/redink/cli.py` — wire `redink audit` to the engine (the stub is already there; replace `cmd_audit`)
- `tests/fixtures/sessions/*.jsonl` — at least three real captures (clean, anti-pattern-heavy, compaction-triggered)
- `tests/test_parser.py`, `tests/test_rules/*.py`, `tests/test_score.py`, `tests/test_report.py`

## What Track A does NOT own

Do NOT touch these — Track B owns them:

- `src/redink/server.py` (the http.server skeleton)
- `src/redink/watcher.py` (the filesystem watcher)
- `src/redink/web/` (index.html, CSS, JS)
- `src/redink/export.py` (HTML export — Track B uses the same template for `watch` and `export`)
- `src/redink/cli.py` `cmd_watch` and `cmd_export` (Track B will replace those)

If you find yourself needing to edit anything in that list, **stop and document the contract change in this file** before proceeding. The merge needs Track B to know.

---

## The shared event contract (DO NOT change without a contract bump)

Define in `src/redink/events.py` — both tracks import from here.

```python
from dataclasses import dataclass
from typing import Literal

EventKind = Literal[
    "turn_start", "turn_content", "tool_call", "file_edit",
    "rule_firing", "turn_end"
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
```

If you need to add a field, append it (don't reorder, don't remove). If you need to add a new event kind, add it and tell Track B in this file.

---

## The five v0.1 rules

Each rule lives in `src/redink/rules/<rule_name>.py`, exposes a `run(turns: list[TurnContent], ...) -> list[RuleFiring]`, and has a docs/rules/<rule_name>.md with a one-paragraph rationale.

### 1. `context_bloat`
**Fires when:** the same text content (>500 tokens) is sent in turn N that was already in context at turn M < N.
**Severity:** warn (or error if >2000 tokens repeated).
**Suggestion:** "This content was already in context at turn {M}. Don't re-paste."

### 2. `compaction_loss`
**Fires when:** Claude Code triggers compaction AND a symbol/path/spec reference that appeared pre-compaction is referenced again post-compaction without being re-loaded via a tool call.
**Severity:** warn.
**Suggestion:** "Reference to '{symbol}' may have been lost in compaction. Read it explicitly."

### 3. `vague_prompt`
**Fires when:** user turn is <15 words AND contains no file path, no symbol name (CamelCase or snake_case identifier >4 chars), no spec section reference, AND is not a confirmation/acknowledgment.
**Severity:** warn.
**Suggestion:** "Add an anchor: which file, which symbol, which section."

### 4. `reexplain_over_tool`
**Fires when:** user turn describes the contents of a file (heuristic: mentions a file path + summarizes its purpose/structure in >50 tokens) when the assistant could have read it via Read/Grep tool.
**Severity:** info.
**Suggestion:** "Let the agent read {file} instead of describing it."

### 5. `brief_miss`
**Fires when:** first user turn of the session is >100 tokens AND does not invoke a brief/bootstrap command (heuristic: no line starting with `Run \`X brief\``).
**Severity:** info.
**Suggestion:** "Cold-start with `<your-brief-cmd> brief` to inject project context in one line."

---

## Token counting (without `tiktoken`)

Use the byte-pair heuristic: `tokens ≈ len(text) / 4` for English-mixed-with-code. Document the imprecision in `docs/rules/context-bloat.md`. Acceptable for v0.1; ADR-002 if precision becomes critical.

---

## Fixtures

Before writing rule code, capture at least three real session files from `~/.claude/projects/`:

1. `tests/fixtures/sessions/clean.jsonl` — a session with no anti-patterns. Should score >85.
2. `tests/fixtures/sessions/bloated.jsonl` — heavy context_bloat + reexplain_over_tool. Should score <60.
3. `tests/fixtures/sessions/compacted.jsonl` — compaction triggered + downstream reference. Should fire compaction_loss.

Ask Danish to point at three of his real sessions, scrub anything sensitive, commit them. Keep them small (<200KB each).

---

## Commit boundaries (Track A)

Each commit should pass `ruff check`, `ruff format --check`, and `pytest`. Use descriptive messages: `feat(parser): ...`, `feat(rules/context-bloat): ...`, `test(parser): ...`.

Commit titles (in order):

1. `feat(events): typed event contract`
2. `feat(parser): claude code jsonl session parser`
3. `test(parser): fixture-driven tests against three real sessions`
4. `feat(rules/context-bloat): detect repeated context across turns`
5. `feat(rules/compaction-loss): detect lost references after compaction`
6. `feat(rules/vague-prompt): detect prompts without an anchor`
7. `feat(rules/reexplain-over-tool): detect file descriptions over tool calls`
8. `feat(rules/brief-miss): detect cold-start without bootstrap`
9. `feat(score): aggregate per-rule firings into summary score`
10. `feat(report): ANSI terminal renderer for redink audit`
11. `feat(cli): wire redink audit to the engine`
12. `docs(rules): one-paragraph rationale per rule`

---

## What Track B is doing in parallel

The other session is building the web UI: stdlib `http.server`, filesystem watcher polling `~/.claude/projects/`, SSE stream, two-panel HTML page. It depends on YOUR `events.py` and `parser.py`. **Push the event contract + parser FIRST so Track B can mock against it.**

Coordinate via the contract in this file. Don't merge breaking contract changes without updating Track B's brief.
