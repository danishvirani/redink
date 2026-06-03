# Track B — redink visualizer (web UI + filesystem watcher + HTML export)

This is a self-contained brief for a fresh Claude Code session working on Track B of redink v0.1. The other track (Track A — the engine: parser + rules + scoring) is being built in parallel by another Claude Code session against the same repo. **Stay in your lane** so we can merge cleanly.

---

## Read these first (in order)

1. `README.md` — what redink is, the demo, the opinion
2. `docs/strategy.md` — why this product, what the brand is
3. `docs/roadmap.md` — the v0.0 → v0.3 build sequence + the parallel-track split
4. `docs/decisions/ADR-001-stdlib-only.md` — the non-negotiable: no runtime deps
5. `docs/sessions/track-a-engine.md` — what the OTHER track is building. Critical for understanding the shared event contract.

Then `cat docs/sessions/track-b-visualizer.md` (this file) and proceed.

---

## What Track B owns

Everything that surfaces the engine's output to a human (live web UI + static HTML export):

- `src/redink/server.py` — stdlib `http.server` that serves `/`, `/events` (SSE), `/api/session/current`
- `src/redink/watcher.py` — polls `~/.claude/projects/*.jsonl` every 250ms, diffs against last seen, emits parsed events
- `src/redink/sse.py` — small SSE helper (stdlib only — `wsgiref` if needed, or hand-rolled chunked HTTP)
- `src/redink/web/index.html` — single self-contained HTML page (Tailwind CDN OK, no build step, vanilla JS or HTMX)
- `src/redink/web/app.js` — vanilla JS that subscribes to `/events` and renders
- `src/redink/web/styles.css` — small overrides on Tailwind
- `src/redink/export.py` — render a complete session into a single self-contained HTML file (no external assets)
- `src/redink/cli.py` `cmd_watch` and `cmd_export` — wire to the server + exporter (stubs are already there; replace)
- `tests/test_server.py`, `tests/test_watcher.py`, `tests/test_export.py`

## What Track B does NOT own

Do NOT touch these — Track A owns them:

- `src/redink/events.py` (the shared event contract — you IMPORT from it, don't modify)
- `src/redink/parser.py` (JSONL → events — you USE it via Track A's API)
- `src/redink/rules/` (the rule engine — you consume `RuleFiring` events)
- `src/redink/score.py`
- `src/redink/report.py` (terminal report — that's Track A's render)
- `src/redink/cli.py` `cmd_audit` (Track A owns the post-hoc CLI)

If you need a contract change (new event kind, new field), **stop and propose it in `docs/sessions/track-a-engine.md` first** so Track A can ship it before you depend on it.

---

## The shared event contract (READ from `src/redink/events.py`)

Track A defines these in `src/redink/events.py`. You import and consume:

```python
from redink.events import (
    TurnStart, TurnContent, ToolCall, FileEdit, RuleFiring, TurnEnd, Event
)
```

You serialize them over SSE as JSON (one event per `data: ...\n\n` block). Same shape for the live stream AND for the static HTML export's embedded session data.

---

## The web UI (single index.html, no build step)

Layout — three regions:

```
+-------------------------------------------------+
|  redink — watching session 4f2a8c (47 turns)    |  <- header
+-------------------------------+-----------------+
|                               |                 |
|  LEFT: Flow                   |  RIGHT:         |
|  (turns as nested cards)      |  Callouts feed  |
|                               |                 |
|  Turn 12 [user]               |  ⚠ Turn 47      |
|   "research the deep ..."     |    context      |
|   • Tool: WebFetch (8 calls)  |    bloat        |
|   • File edit: notes.md       |    8.2k tokens  |
|                               |    [fix this]   |
|  Turn 13 [assistant]          |                 |
|   ...                         |  ✓ Turn 19      |
|                               |    brief boot   |
+-------------------------------+-----------------+
|  Cost: $0.42  •  Time: 12m 34s  •  [share]     |  <- status bar
+-------------------------------------------------+
```

Stack:
- **HTML**: single file, semantic, ARIA labels where it matters
- **CSS**: Tailwind via CDN (acceptable because it's CSS-only at runtime, not a JS framework). Small overrides in `styles.css`.
- **JS**: vanilla. `EventSource("/events")` for SSE. State held in a single `session` object updated event-by-event. No virtual DOM, no framework.
- **No build step.** Files are served as-is by `server.py`.

Constraints (from ADR-001):
- No npm, no Node, no build pipeline, no bundler.
- The HTML file should be human-readable when you View Source.
- The static export must be a SINGLE file with everything inlined (CSS inline, JS inline, no external assets — Tailwind classes get inlined or replaced).

---

## Filesystem watcher (stdlib only, no `watchdog`)

`src/redink/watcher.py`:

```python
def watch(projects_dir: Path, on_event: Callable[[Event], None], stop: Event) -> None:
    """Poll projects_dir for JSONL session updates every 250ms.
    
    For each session file, track the byte offset we last read to.
    On change, read new bytes, parse new lines via Track A's parser,
    run the rule engine, and emit events to `on_event`.
    """
```

Polling at 250ms is acceptable for v0.1. Document the CPU cost in the rationale ("burns ~0.3% CPU continuously"). If users complain, ADR-002 to take a `watchdog` dep — but not before complaints.

---

## SSE without external deps

stdlib `http.server` doesn't ship SSE primitives, but it's straightforward:

```python
def handle_events(self):
    self.send_response(200)
    self.send_header("Content-Type", "text/event-stream")
    self.send_header("Cache-Control", "no-cache")
    self.send_header("Connection", "keep-alive")
    self.end_headers()
    
    while not self.server.shutdown_requested:
        event = self.server.event_queue.get(timeout=1.0)
        self.wfile.write(f"data: {json.dumps(event_to_dict(event))}\n\n".encode())
        self.wfile.flush()
```

Use a threading.Queue between the watcher thread and each connected SSE handler.

---

## Static HTML export

`redink export <session.jsonl>` renders the same template used by the live UI, but with the full event stream embedded in a `<script type="application/json" id="session-data">...</script>` tag. The vanilla JS in the page reads from that tag instead of subscribing to SSE.

Same code path for live and static — just different event source.

The exported HTML must be:
- A single file (everything inlined)
- Openable in any modern browser by double-clicking
- Pasteable in Slack as an attachment, droppable in a GitHub gist
- <500KB for a typical 47-turn session

---

## Commit boundaries (Track B)

Each commit should pass `ruff check`, `ruff format --check`, and `pytest`. Use descriptive messages.

Commit titles (in order):

1. `feat(server): stdlib http.server skeleton serving index.html + /events`
2. `feat(web): two-panel layout in single index.html (Tailwind CDN, vanilla JS)`
3. `feat(sse): event stream from server to browser`
4. `feat(watcher): poll ~/.claude/projects for JSONL changes, emit events`
5. `feat(web/flow): render TurnStart/TurnContent/ToolCall/FileEdit as nested cards`
6. `feat(web/callouts): render RuleFiring as inline alerts with "fix this"`
7. `feat(web/status): cost ticker + elapsed timer in bottom bar`
8. `feat(export): static HTML export with embedded session data`
9. `feat(cli): wire redink watch + redink export`
10. `test(server,watcher,export): coverage for the surfaces`

---

## Sequencing with Track A

Track A is shipping the engine + event contract FIRST. Coordinate:

1. **Wait for Track A's commit 1** (`feat(events): typed event contract`) before writing any code that imports `redink.events`.
2. **Wait for Track A's commit 2** (`feat(parser): claude code jsonl session parser`) before wiring the watcher. Until then, use a mock parser that emits hand-crafted events from a static fixture.
3. **Wait for Track A's commit 9** (`feat(score): ...`) before wiring score display in the status bar.
4. **Wait for Track A's commits 4-8** (the five rules) before rules fire in your UI. Until then, hand-craft `RuleFiring` events in fixtures.

Push your work to a branch (`track-b-visualizer`) and rebase onto main as Track A's commits land. Open a draft PR early so Track A can see what you're depending on.

---

## What Track A is doing in parallel

The other session is building the engine: parser, five rules, score aggregator, ANSI terminal renderer, `redink audit` wiring. They produce the events you consume. **Don't fork the event contract.**
