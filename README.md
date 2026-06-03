# redink

> Opinionated audits for AI coding sessions. The senior reviewer's red ink on your Claude Code work.

Install:

```bash
curl -fsSL https://raw.githubusercontent.com/danishvirani/redink/main/install.sh | sh
```

No pip-install-langchain-langgraph-redis. No Node. No Docker. Python 3.10+ is all you need.

## What it does

You give it a Claude Code session log. It hands you back the same session marked up — like a senior reviewer's red ink on a draft.

```
$ redink audit ~/.claude/projects/my-project/session.jsonl

redink — audit of session 4f2a8c... (2026-06-03, 47 turns)

  Turn 12  ✗ Sent 8,200 tokens of CLAUDE.md verbatim, already in context
  Turn 19  ✓ Excellent brief-driven bootstrap
  Turn 23  ✗ Vague prompt "fix it" with no anchor
  Turn 28  ✗ Re-read auth.ts already loaded in turn 9
  Turn 33  ✓ Tool call beat re-explaining
  Turn 41  ✗ Compaction triggered, lost the spec reference

Score: 64/100
  Context efficiency   58
  Prompt clarity       71
  Tool usage           89
  Anti-patterns        4 flagged
  Cost waste (est.)    $0.42 / session
```

## The opinion

Most AI tooling scoring tells you you're amazing. redink tells you what a senior engineer reviewing your PR would say.

- Context should stay under 100k tokens. Compression loses what matters.
- Brief-driven bootstrap beats 500-word cold prompts. Every time.
- Most turns waste tokens by re-sending context the model already has.
- Vague prompts get vague output. The fix is anchoring, not retry.
- Tool calls > re-explaining > apologizing.

The full reasoning is in [docs/strategy.md](docs/strategy.md). [ADR-001](docs/decisions/ADR-001-stdlib-only.md) explains why redink is stdlib-only — no httpx, no pydantic, no rich. The install command stays one shell line forever.

## Three examples

```bash
# 1. Audit the most recent session in the current project
redink audit

# 2. Audit a specific session log, print to terminal
redink audit ~/.claude/projects/foo/4f2a8c.jsonl

# 3. Export a single shareable HTML report
redink export 4f2a8c.jsonl > review.html
# Open in a browser. Send to a colleague. Paste in Slack.
```

## Status

v0.0 — scaffold. CLI surface is wired, scoring stubs return placeholders. v0.1 ships the real audit engine with 5 rule types. See [`docs/roadmap.md`](docs/roadmap.md).

## License

MIT. See [LICENSE](LICENSE).

## Thanks

Built by [Danish Virani](https://github.com/danishvirani). The design inheritance is obvious: `jq`, `grep`, Simon Willison's `llm`, Mitchell Hashimoto's writing on Ghostty.

The thesis: AI tooling should ship with an opinion, not a fluency score.
