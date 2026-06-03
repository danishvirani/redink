# redink — build roadmap

Date: 2026-06-03
Status: v0.0 (scaffold)

Engineering plan, not a marketing roadmap. Each version is a real, shippable artifact a stranger can install and use. Ship when the DoD line below is true.

---

## v0.0 — scaffold (current)

**What works:**
- `redink -h` renders, lists `audit`, `export`, `version`
- `redink version` prints `redink 0.0.1`
- `redink audit [path]` accepts input, exits 1 with a "not yet implemented" message that points at the roadmap
- `redink export <path>` same shape
- `pip install -e ".[dev]"` works
- `./install.sh` writes a launcher at `~/.local/bin/redink`
- CI passes: ruff lint + ruff format + pytest on Python 3.10/3.11/3.12 across Ubuntu + macOS

**What does NOT work yet:**
- Audit rules return stubs
- Export returns a stub
- No HTML template yet
- Cursor / Codex CLI parsers not implemented

**DoD:** ✅ shipped. Tests green, install verified.

---

## v0.1 — real audits

The first version someone can do real work with. Single command, real Claude Code session, real opinionated output.

**DoD:** `redink audit <session.jsonl>` against a real Claude Code session produces a marked-up terminal report. Five rule types implemented. Per-turn callouts. Summary score block. "What to do" tail.

**Commits in order:**

1. **JSONL session parser** — read Claude Code session format, emit a typed stream of turn events. `tests/fixtures/sessions/` with at least three real captures (clean session, anti-pattern-heavy session, compaction-triggered session).
2. **Rule: context bloat** — token count of repeated content across turns. Threshold + suggestion.
3. **Rule: compaction loss** — detect when compaction dropped a symbol that's referenced later.
4. **Rule: vague prompt** — heuristic on prompt anchoring (file path? symbol name? spec section reference?).
5. **Rule: re-explain over tool** — pattern detection on described-vs-readable file content.
6. **Rule: brief miss** — first-turn pattern detection for a brief-bootstrap line.
7. **Terminal report renderer** — ANSI red ✗ + green ✓ + dim gray, per-turn lines, summary score block, "what to do" closing paragraph.
8. **Per-rule rationale docs** — `docs/rules/*.md`, one paragraph each with the opinion behind the rule.
9. **`redink audit <project>`** — auto-discover the most recent session in a project directory.

**Risks / unknowns:**
- Claude Code session format may evolve. Mitigation: fixture-pin tests; ADR-002 if a format break forces action.
- Anthropic's 4D Fluency Framework may be adopted as the canonical scoring rubric. Mitigation: redink scores against ITS opinions, not the framework. The framework is a vocabulary, not a rubric we adopt wholesale.
- Tokenizer accuracy without a deps for `tiktoken`. Mitigation: byte-pair heuristic + documented imprecision in the rationale.

**README diff when this ships:** drop "v0.0 scaffold" framing; add real example output; bump version.

---

## v0.2 — shareable HTML + Cursor support

Make the artifact actually shareable. Add the second log source.

**DoD:**
- `redink export <session.jsonl> > review.html` produces a self-contained HTML file (inline CSS, no external assets, no JS framework, no fonts). Opens in any browser, renders the audit, looks polished.
- `redink audit <cursor-workspace>` parses Cursor's SQLite session and runs the same rules.

**Commits in order:**

1. **HTML template** — stdlib `string.Template` or hand-rolled escaping, inline CSS, no external deps. One template, parameterized.
2. **`redink export`** — write rendered HTML to stdout or `--out path/`.
3. **Cursor SQLite parser** — read Cursor's local workspace SQLite, emit the same typed turn event stream.
4. **Auto-detect source** — `redink audit <some-dir>` figures out which agent's logs to read (Claude Code project dir vs Cursor workspace).
5. **`docs/sharing.md`** — patterns for the exported HTML: Slack share, GitHub gist embed, paste-as-attachment in PR comments.

**Risks / unknowns:**
- Cursor's SQLite is undocumented. If the format proves unstable, defer Cursor and ship Claude-Code-only HTML export.
- "Self-contained HTML" gets large for long sessions. Truncate intelligently, link to source for full text.

---

## v0.3 — live mode + Claude Code plugin + MCP server

The wrapper layer. Same core, three surfaces, no branching logic.

**DoD:**
- `redink audit --watch` updates a terminal view in real time as the agent runs (filesystem watcher on `~/.claude/projects/`, ANSI redraw).
- `plugins/redink/` installs into `~/.claude/plugins/redink/`. Slash commands `/redink-audit` and `/redink-export` work.
- `redink mcp` starts a stdio MCP server exposing `audit(session_path)` and `export(session_path)` as tools.

**Commits in order:**

1. **`--watch` mode** — polling filesystem watcher (no `watchdog` dep), in-place ANSI redraw.
2. **`plugins/redink/.claude-plugin/plugin.json`** + command markdown files.
3. **`redink-bootstrap` skill** that auto-loads on session start.
4. **`redink mcp` server** — hand-rolled stdio JSON-RPC, ~150 lines, no SDK dep.
5. **README sections become real** — drop "deferred" framing; add Claude Code + MCP install instructions.

**Risks / unknowns:**
- Anthropic may ship a built-in audit feature. Mitigation: redink's OPINION is the wedge; built-in tools won't be opinionated, they'll be neutral.
- MCP spec churn. Pin to the version tested, document it.

---

## Beyond v0.3 (radar, not committed)

- Codex CLI parser
- Gemini Code Assist log parser
- `redink rule add` — user-defined rules via YAML
- `redink history` — trend chart across sessions of a project
- `redink diff <session-a> <session-b>` — what improved/regressed between two sessions
- PyPI publish (curl-install stays the canonical install; `pipx install redink` is the fallback)

## What would make us slow down or pivot

- **v0.1 ships, audit works, but the opinion doesn't land.** If "your context is bloated" gets eye-rolls instead of "oh shit yes," the opinion is wrong. Rewrite the rules, not the tool.
- **Anthropic ships a built-in audit with sharper opinions.** Unlikely (vendors don't ship "you're using our product wrong" tools) but possible. Then we differentiate on cross-agent + HTML export.
- **The audience doesn't materialize.** v0.1 + public README + one HN post. If it doesn't land, the opinion was either wrong or wanted. Iterate or kill.
- **Claude Code session format breaks incompatibly.** Version-pin and ship an `upgrade` subcommand.
