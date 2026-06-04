# Rule: context_bloat

**Fires when** a block of text over the threshold (default 500 estimated
tokens) is sent in a turn after the same block already appeared in an earlier
turn. Severity is `error` above 2,000 repeated tokens, `warn` otherwise.

**Why it's the #1 opinion.** Re-sending context the model already has is the
single most common token-waste anti-pattern. Pasting a spec, a file dump, or a
CLAUDE.md a second time doesn't help the model — it already has the content in
context — and you pay input tokens for every repeat. The fix is never "paste it
again"; it's to reference the earlier turn, or let the agent re-read the source
with a tool call if it genuinely fell out of context.

**Threshold:** `context_bloat_min_tokens` (500), `context_bloat_error_tokens`
(2000), both on `RuleConfig`.

**Token-count imprecision (ADR-001).** redink counts tokens with the heuristic
`len(text) // 4` — roughly 4 characters per token for English mixed with code.
This is deliberately not `tiktoken`: a compiled C extension would break the
"any Python 3.10+ works, one curl line to install" promise (ADR-001). The
heuristic runs ~10–20% off a real BPE tokenizer depending on content, which is
fine for this rule — we're flagging blocks re-sent at the thousand-token scale,
not billing by the token. If precision ever becomes load-bearing, that's an
ADR-002 decision to vendor a pure-Python tokenizer.
