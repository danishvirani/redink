# Rule: brief_miss

**Fires when** the first real user prompt of a session is over the token
threshold (default 100 estimated tokens) and does not invoke a brief/bootstrap
command — heuristically, a backticked ``X brief`` line. Severity `info`, once
per session, on the opening turn.

**Why it matters.** Brief-driven bootstrap beats a 500-word cold prompt, every
time. A ``<your-tool> brief`` line injects the project's context — conventions,
architecture, where things live — in a single line the agent expands on demand,
instead of you hand-typing (and re-typing, session after session) a wall of
preamble that's already written down somewhere. The long cold prompt is also
where context bloat starts: you front-load everything because you're afraid the
agent won't have it, and half of it the agent never needed. A brief command
keeps the opening turn small and the context lean. This fires `info`, not
`warn`: a long opener isn't wrong, it's just a missed chance to start lean.

**Threshold:** `brief_miss_min_tokens` (100) on `RuleConfig`. The brief-command
detection is intentionally loose (any backticked phrase containing "brief"), so
it recognizes whatever bootstrap command your project uses.
