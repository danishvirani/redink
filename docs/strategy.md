# redink — strategy

Date: 2026-06-03
Status: pre-v0.1
Audience: me (Danish). Forward to teammates if helpful.

This is the "why redink exists, why this shape" doc. Build sequence is in [roadmap.md](roadmap.md). The single biggest engineering decision is in [decisions/ADR-001-stdlib-only.md](decisions/ADR-001-stdlib-only.md).

---

## The call

After surveying six adjacent product shapes — deep-research CLI, AI commerce protocol emulator, deploy-patterns init, AI Lighthouse, create-ai-cli scaffolder, live agent visualizer — the surviving angle is:

**An opinionated, score-first, cross-agent audit CLI for AI coding sessions. Lead with the opinion. The HTML export is the share artifact. Live mode exists but isn't the lede.**

### Why not the others

- **AI commerce protocol emulator** — NDA exposure. Killed.
- **Live agent visualizer alone** — Eight tools shipped this between research and our build. `tombelieber/claude-view` v0.44 shipped June 3 with live SSE + tool-call cards + share URLs + an experimental AI Fluency Score. Red ocean.
- **AI Lighthouse alone** — Scoring went from empty (March 2026) → occupied (April) → commodity (June). The Anthropic 4D Fluency Framework + claude-view's score + GitVelocity's `/ai-fluency` skill have already shipped the obvious version.
- **Deep-research CLI** — Solid B+ helpful, not visceral pain.
- **Deploy-patterns init** — Real market timing window (AWS Copilot EOL June 12, Heroku in sustain mode) but read as not-cool-enough for personal-brand goals. Parked.
- **create-ai-cli scaffolder** — Real gap, weekend build. Parked as a possible second project.

### Why redink survives

- The space converged on a single fluency number. redink ships **per-turn opinionated callouts** instead.
- Competitor opinions are weak: "your context efficiency is 73." redink's are sharp: "Turn 12 re-sent 8,200 tokens of CLAUDE.md already in context. Don't do that."
- Cross-agent (Claude Code + Cursor + Codex CLI logs) widens the moat over single-source competitors.
- Self-contained HTML export is a sharable artifact in a category where competitors ship dashboards.
- NDA-clean: AI tool usage analysis is not AI commerce.

---

## The opinion (the brand)

The brand IS the opinion. Repeat verbatim — README, ADRs, commit messages, any future writing.

- **Context should stay under 100k tokens.** Compression loses what matters. Frequent compaction means you're working too long without resetting.
- **Brief-driven bootstrap beats 500-word cold prompts.** Every time.
- **Most turns waste tokens.** Re-sent context the model already has is the #1 anti-pattern.
- **Vague prompts get vague output.** The fix is anchoring (file, symbol, spec section), not retry.
- **Tool calls > re-explaining > apologizing.**

### Anti-positioning — what we will NOT do

- No "Fluency Score" naming. That phrase is commoditizing. We don't compete on terms everyone uses.
- No hosted dashboard. Local only. HTML export for sharing.
- No "your usage is great!" copy. redink only fires when there's a real problem to fix.
- No telemetry. We don't phone home; users don't expect us to.
- No "AI-powered" / "revolutionary" copy. We sound like the engineer giving honest feedback, not the marketing team.

### Reference engineers (study their posture, not their content)

- **Mitchell Hashimoto** — for the writing voice. Long-form, technically honest, never plays the founder card.
- **Simon Willison** — for the cadence. Datasette, llm, files-to-prompt — ship + explain + move on.
- **Julia Evans** — for the explanatory voice. Curiosity-first, never preachy.

Borrow opinionation, skip DHH-style picking-fights energy. The opinion lands harder matter-of-fact.

---

## v0.1 scope summary

**DoD:** `redink audit <session.jsonl>` against a real Claude Code session produces an opinionated terminal report. 5 rule types implemented. Per-turn callouts. Summary score. "What to do" tail.

**Five v0.1 rule types:**

1. **Context bloat** — N tokens of content sent that were already in context
2. **Compaction loss** — compaction triggered and a critical reference was lost downstream
3. **Vague prompt** — prompt with no file/symbol/spec anchor
4. **Re-explain over tool** — described file contents that could have been read via tool call
5. **Brief miss** — session started without a brief-bootstrap pattern

Each rule has a one-paragraph rationale in `docs/rules/`, a configurable threshold, and a "fix this" suggestion in the output. The full build order is in [`roadmap.md`](roadmap.md).
