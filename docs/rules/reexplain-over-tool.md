# Rule: reexplain_over_tool

**Fires when** a prompt over the token floor (default 50 estimated tokens) names
a file path and then describes that file's existing contents — detected by
description markers like "contains", "defines", "which takes". Severity `info`.

**Why it matters.** Tool calls beat re-explaining. When you name a file and then
spend a paragraph telling the agent what's in it, you pay two costs: the tokens
for a description the agent didn't need, and the risk that your description is
stale or subtly wrong — the file on disk is the source of truth, your memory of
it isn't. Letting the agent `Read` the file is cheaper and always accurate. The
rule is careful to fire only on *descriptions of existing code* ("contains a
function which takes…"), not on requests for *new* code ("add a helper that
maps…"), which legitimately name a file without re-explaining it.

**Threshold:** `reexplain_min_tokens` (50) on `RuleConfig`. Severity is `info`
because this is a habit worth nudging, not a costly error.
