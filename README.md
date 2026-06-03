# redink

> Watch your Claude Code session live, with red ink in the margins. Opinionated, local, no telemetry.

Install:

```bash
curl -fsSL https://raw.githubusercontent.com/danishvirani/redink/main/install.sh | sh
```

No pip-install-langchain-langgraph-redis. No Node. No Docker. Python 3.10+ is all you need.

## The demo

```bash
redink watch
# → http://localhost:8787 opens
```

Run Claude Code in another terminal. The browser fills in live:

- **Left**: the flow of your session — every turn, tool call, file edit, with diffs
- **Right**: opinionated callouts as they happen — *"Turn 47: about to re-send 8.2k tokens already in context"*
- **Bottom**: cost ticking, time elapsed, [share] button that produces a single self-contained HTML file

When the session ends, the static export captures the whole thing — drop it in Slack, attach it to a PR, paste it in a doc.

## What it tells you (the opinion)

Most AI tooling scoring tells you you're amazing. redink tells you what a senior engineer reviewing your PR would say.

```
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

You can also run it post-hoc on a saved session without the live UI:

```bash
redink audit ~/.claude/projects/my-project/4f2a8c.jsonl
# Same rules, terminal report instead of web UI
```

## The five opinions baked in

- Context should stay under 100k tokens. Compression loses what matters.
- Brief-driven bootstrap beats 500-word cold prompts. Every time.
- Most turns waste tokens by re-sending context the model already has.
- Vague prompts get vague output. The fix is anchoring, not retry.
- Tool calls > re-explaining > apologizing.

The full reasoning is in [docs/strategy.md](docs/strategy.md). [ADR-001](docs/decisions/ADR-001-stdlib-only.md) explains why redink is stdlib-only — no httpx, no pydantic, no rich. The install command stays one shell line forever.

## Command surface

```bash
redink watch                     # live web UI on :8787, the lede
redink audit [<session-path>]    # post-hoc terminal report
redink export <session> > out.html  # static, self-contained, shareable
redink version
```

## Status

v0.0 — scaffold. The CLI surface is wired, scoring stubs return placeholders, `watch` server is not yet running. v0.1 ships the real engine: live web UI + 5 opinion rules + HTML export. See [`docs/roadmap.md`](docs/roadmap.md).

## License

MIT. See [LICENSE](LICENSE).

## Thanks

Built by [Danish Virani](https://github.com/danishvirani). The design inheritance is obvious: `jq`, `grep`, Simon Willison's `llm`, Mitchell Hashimoto's writing on Ghostty.

The thesis: AI tooling should ship with an opinion, not a fluency score.
