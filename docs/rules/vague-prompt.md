# Rule: vague_prompt

**Fires when** a real user prompt is under the word threshold (default 15
words), names no anchor (file path, code symbol, or spec section), and is not an
acknowledgment. Severity `warn`.

**Why it matters.** "just fix it", "make it better", "try again" — short,
anchorless prompts get vague output, and the instinct to *retry* the vague
prompt wastes a turn producing more vague output. The fix is anchoring, not
retrying: name the file, the function, or the section, and the next response
sharpens immediately. Acknowledgments ("yes", "ship it", "sounds good") are also
short and anchorless but aren't instructions, so they're explicitly excluded —
firing on every "yes" would be noise that trains you to ignore the tool.

**Threshold:** `vague_prompt_max_words` (15) on `RuleConfig`. Anchor and
acknowledgment detection live in `rules/_text.py`.
