# redink — build roadmap

Date: 2026-06-03
Status: v0.0 (scaffold)

Engineering plan, not a marketing roadmap. Each version is a real, shippable artifact a stranger can install and use. Ship when the DoD line below is true.

**v0.1 is parallelizable across two Claude Code sessions.** Track A is the engine (parser + rules + CLI audit). Track B is the surface (web UI + filesystem watcher + HTML export). They share a typed event interface. Per-track session prompts: [sessions/track-a-engine.md](sessions/track-a-engine.md) and [sessions/track-b-visualizer.md](sessions/track-b-visualizer.md).

---

## v0.0 — scaffold (current)

**What works:**
- `redink -h` renders, lists `watch`, `audit`, `export`, `version`
- `redink version` prints `redink 0.0.1`
- `redink watch`, `redink audit`, `redink export` accept input, exit 1 with "not yet implemented"
- `pip install -e ".[dev]"` works
- `./install.sh` writes a launcher at `~/.local/bin/redink`
- CI passes: ruff lint + ruff format + pytest on Python 3.10/3.11/3.12 across Ubuntu + macOS

**What does NOT work yet:**
- The engine (parser + rules) is unwritten
- The web UI is unwritten
- The HTML export is unwritten

**DoD:** ✅ shipped.

---

## v0.1 — the live UI + the engine that powers it

The first version someone can actually use. Live web UI is the lede; the CLI audit + HTML export use the same engine.

**DoD (all three must be true):**

1. `redink watch` opens `:8787`, shows live flow + live callouts + cost ticker, updates as Claude Code writes to `~/.claude/projects/`.
2. `redink audit <session.jsonl>` runs the same engine post-hoc and prints an ANSI terminal report.
3. `redink export <session.jsonl>` writes a single self-contained HTML file (no external assets) with the full audit.

### Track A — the engine (one Claude Code session)

Owns: parser, rules, scoring, terminal report renderer.
Brief: [sessions/track-a-engine.md](sessions/track-a-engine.md).

**Commits in order:**

1. **JSONL session parser** — read Claude Code session format, emit a typed stream of turn events. `tests/fixtures/sessions/` with at least three real captures.
2. **Rule: context bloat** — token count of repeated content across turns. Threshold + "fix this" suggestion.
3. **Rule: compaction loss** — detect when compaction dropped a symbol that's referenced later.
4. **Rule: vague prompt** — heuristic on prompt anchoring (file path? symbol name? spec section reference?).
5. **Rule: re-explain over tool** — pattern detection on described-vs-readable file content.
6. **Rule: brief miss** — first-turn pattern detection for a brief-bootstrap line.
7. **Terminal report renderer** — ANSI red ✗ + green ✓ + dim gray, per-turn lines, summary score block, "what to do" tail.
8. **Per-rule rationale docs** — `docs/rules/*.md`, one paragraph each.
9. **`redink audit <project>`** — auto-discover the most recent session in a project directory.

### Track B — the visualizer (the other Claude Code session)

Owns: web server, filesystem watcher, SSE pipeline, HTML template (both for live UI and static export), front-end HTML/CSS/JS.
Brief: [sessions/track-b-visualizer.md](sessions/track-b-visualizer.md).

**Commits in order:**

1. **stdlib `http.server` skeleton** — serves the single index.html, defines the `/events` SSE endpoint.
2. **Filesystem watcher** — polls `~/.claude/projects/*.jsonl` every 250ms, diffs against last seen, emits parsed events via SSE.
3. **Single index.html** — two-panel layout (flow tree left, callouts right, status bar bottom), Tailwind CDN, vanilla JS subscribing to `/events`.
4. **Flow tree component** — render turns + tool calls + file edits as nested cards.
5. **Callout component** — receives rule firings from the engine, displays as live inline alerts with "fix this" suggestions.
6. **Cost ticker + elapsed timer** — bottom status bar.
7. **Share button → static HTML export** — same template, but renders the WHOLE captured session at the moment of export, fully self-contained (no external assets, no JS framework). This is also what `redink export <session.jsonl>` uses.

### Shared contract

Both tracks consume/produce a single typed event stream:
- `TurnStart(turn_id, role, ts)`
- `TurnContent(turn_id, text, token_count_est)`
- `ToolCall(turn_id, tool, args, response)`
- `FileEdit(turn_id, path, diff)`
- `RuleFiring(turn_id, rule_id, severity, message, suggestion)`
- `TurnEnd(turn_id, total_tokens, cost_est)`

Defined in `src/redink/events.py`. Track A produces; Track B consumes (and re-emits over SSE).

**Risks / unknowns:**
- Claude Code session format may evolve. Mitigation: fixture-pin tests + ADR-002 if a format break forces action.
- claude-view (and others) may add opinionated mode. Mitigation: our opinion is sharper + cross-agent comes in v0.2.
- Tokenizer accuracy without `tiktoken`. Mitigation: byte-pair heuristic, document imprecision in `docs/rules/context-bloat.md`.

**README diff when v0.1 ships:** drop "scaffold" framing, add a 15-second screencast, bump version.

---

## v0.2 — cross-agent + smart warnings

Make redink work for users who aren't on Claude Code AND start nudging users in real time, not just scoring them post-hoc.

**DoD:**
1. `redink audit <cursor-workspace>` and `redink watch --source cursor` work against Cursor's SQLite session storage with the same rule engine.
2. Live UI surfaces proactive warnings when context approaches threshold and suggests delegating to a sub-agent.

**Commits:**
1. **Cursor SQLite parser** — read workspace SQLite, emit the same typed turn events.
2. **Auto-detect source** — `redink audit <dir>` figures out which agent's logs to read.
3. **Codex CLI parser** — same shape, smaller fixtures.
4. **Rule: context-budget warning** — when running token total exceeds 80k, fire a warn-level callout: "Context at 82% of budget. Consider summarizing or spawning a sub-agent."
5. **Rule: sub-agent suggestion** — heuristic: turn spawns >3 tool calls on a tangentially-related task → fire info-level "This subtask could be delegated to a sub-agent to keep main context clean."
6. **Polish pass** — dark mode, copyable callout text, keyboard shortcuts for scrubbing.
7. **`docs/sharing.md`** — patterns for using exported HTML in Slack, GitHub gists, PR comments.

---

## v0.3 — interventions + Claude Code plugin + MCP server

The wrapper layer + the actions. redink stops being purely observational and starts helping you save state before things go wrong.

**DoD:**
- `plugins/redink/` installs into `~/.claude/plugins/redink/`. Slash commands `/redink-watch`, `/redink-audit`, `/redink-snapshot` work.
- `redink mcp` starts a stdio MCP server exposing `audit`, `export`, `current_score`, `snapshot_to` as tools.
- `redink snapshot --to linear AGX-123` (or `--to notion <page>`, `--to gist`, `--to file ~/notes/`) captures the current session's context + decisions and saves them outside the session, so the next session can resume cleanly.

**Commits:**
1. **`plugins/redink/.claude-plugin/plugin.json`** + command markdown files.
2. **`redink-bootstrap` skill** that auto-loads on session start.
3. **`redink mcp` server** — hand-rolled stdio JSON-RPC, ~150 lines, no SDK dep.
4. **`redink snapshot`** core — extract session decisions + key file references + open questions into a structured summary.
5. **Snapshot destination: file** — write to `~/notes/redink-snapshots/` as markdown.
6. **Snapshot destination: GitHub Gist** — via `gh` CLI if installed, fallback to clipboard.
7. **Snapshot destination: Linear** — via API key, append a comment or create a sub-ticket on the parent. (Generic enough to ship — same pattern as agentix-cli's heredoc create.)
8. **Snapshot destination: Notion** — via API key, append to a configured page.
9. **README sections become real** — drop "deferred" framing.

---

## Beyond v0.3 (radar, not committed)

- **Auto-compact** — when context exceeds threshold, redink offers an inline "Snapshot + reset" action that captures the session state to the configured destination, gives you a 1-line "where to pick up" summary, and lets you start a fresh Claude Code session with that summary pre-loaded. This is the killer "redink saved my session" moment. Bigger feature; needs careful UX.
- Gemini Code Assist log parser
- `redink rule add` — user-defined rules via YAML
- `redink history` — trend chart across sessions of a project
- `redink diff <session-a> <session-b>` — what improved/regressed
- PyPI publish (curl-install stays the canonical install; `pipx install redink` is the fallback)

## What would make us slow down or pivot

- **v0.1 ships, the opinion doesn't land.** If "your context is bloated" gets eye-rolls instead of "oh shit yes," rewrite the rules, not the tool.
- **A competitor ships opinionated visualizations before v0.1.** Then we differentiate on cross-agent + HTML export.
- **Audience doesn't materialize after public launch.** Iterate the opinion or kill.
- **Claude Code session format breaks incompatibly.** Version-pin, ship an `upgrade` subcommand.
