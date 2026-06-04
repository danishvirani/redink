# Rule: compaction_loss

**Fires when** Claude Code triggers compaction and a symbol or file path that
was loaded *before* the compaction boundary is referenced again *after* it,
without being re-read via a `Read`/`Grep`/`Glob` tool call in between. Severity
`warn`, one firing per lost reference.

**Why it matters.** Compaction summarizes earlier context and discards the
detail to free up the window. That's the right move when you've been working too
long — but it's lossy. If the model goes on to edit `validate_schema` using only
a one-line summary of what `validate_schema` was, it's working blind, and the
edit is a coin flip. The opinion: context should stay under ~100k tokens so you
rarely compact at all; but when you do, re-load the things you're about to touch
rather than trusting the summary. A `Read` of the symbol between the boundary
and the reference suppresses the firing — that's exactly the behavior we want to
reward.

**Threshold:** none configurable in v0.1 — presence of a compaction boundary
plus a stale reference is the trigger. Symbol detection is heuristic
(snake_case, CamelCase, file paths), so it can miss prose-only references; it
favors precision over recall.
