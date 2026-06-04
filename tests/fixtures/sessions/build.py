"""Generate the three redink test fixtures in real Claude Code JSONL format.

Why synthetic (not captured): real sessions in this author's projects are
NDA-covered, and — critically — no real session exhibits verbatim context
re-paste (prompt caching makes it unnecessary), so the ``bloated`` profile has
to be authored regardless. These fixtures are byte-accurate to the Claude Code
schema (message blocks, tool_use/tool_result pairing, compactMetadata, usage)
but carry zero protected content. The subject is a fictional structured-logging
CLI ("tinylog").

Run: ``python tests/fixtures/sessions/build.py`` — rewrites the three .jsonl
files next to this script. Deterministic output (fixed ids + timestamps).

The fixtures are designed so the v0.1 rule engine fires deterministically:
  clean.jsonl     -> no rules fire (brief-driven, anchored, tool-first)
  bloated.jsonl   -> context_bloat + reexplain_over_tool + vague_prompt + brief_miss
  compacted.jsonl -> compaction_loss (symbol referenced across a compaction)
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent

# A ~9 KB generic "format spec" used as the context-bloat payload. Repeating
# this verbatim across two turns is what trips context_bloat (>2000 tokens).
SPEC_BLOCK = "## tinylog line format specification\n\n" + "\n".join(
    f"- field {i:02d}: column `f{i:02d}` is rendered left-padded to width 12, "
    f"ANSI-colored by severity, separated from the next field by a single space, "
    f"and truncated with an ellipsis when it exceeds the configured column budget "
    f"of 80 characters for terminal output mode number {i}."
    for i in range(1, 60)
)


class Builder:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.lines: list[dict] = []
        self._uuid = 0
        self._clock = 0
        self._tool = 0

    def _next_uuid(self) -> str:
        self._uuid += 1
        return f"{self.session_id}-{self._uuid:04d}"

    def _next_ts(self) -> str:
        self._clock += 30
        m, s = divmod(self._clock, 60)
        return f"2026-06-04T10:{m:02d}:{s:02d}.000Z"

    def _base(self, type_: str) -> dict:
        return {
            "type": type_,
            "uuid": self._next_uuid(),
            "timestamp": self._next_ts(),
            "sessionId": self.session_id,
            "cwd": "/Users/dev/code/tinylog",
            "gitBranch": "main",
            "version": "2.0.0",
        }

    def user(self, text: str) -> "Builder":
        line = self._base("user")
        line["message"] = {"role": "user", "content": text}
        self.lines.append(line)
        return self

    def assistant(self, text: str, tools: list[dict] | None = None) -> list[str]:
        content: list[dict] = []
        if text:
            content.append({"type": "text", "text": text})
        ids: list[str] = []
        for tool in tools or []:
            self._tool += 1
            tid = f"toolu_{self.session_id}_{self._tool}"
            ids.append(tid)
            content.append(
                {"type": "tool_use", "id": tid, "name": tool["name"], "input": tool["input"]}
            )
        line = self._base("assistant")
        line["message"] = {
            "role": "assistant",
            "model": "claude-sonnet-4-5",
            "content": content,
            "usage": {
                "input_tokens": 1200,
                "output_tokens": 320,
                "cache_read_input_tokens": 18000,
                "cache_creation_input_tokens": 0,
            },
        }
        self.lines.append(line)
        return ids

    def tool_result(self, tid: str, text: str) -> "Builder":
        line = self._base("user")
        line["message"] = {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": tid, "content": text}],
        }
        self.lines.append(line)
        return self

    def compaction(self, pre_tokens: int = 162000) -> "Builder":
        line = self._base("system")
        line["subtype"] = "compact_boundary"
        line["isMeta"] = True
        line["content"] = ""
        line["compactMetadata"] = {"trigger": "auto", "preTokens": pre_tokens}
        self.lines.append(line)
        return self

    def write(self, name: str) -> None:
        out = HERE / name
        with out.open("w", encoding="utf-8") as fh:
            for line in self.lines:
                fh.write(json.dumps(line) + "\n")


def build_clean() -> None:
    b = Builder("clean000")
    # Brief-driven bootstrap (no brief_miss), anchored prompts, tool-first.
    b.user(
        "Run `tinylog brief` to load project context. Then add a `parse_level` "
        "helper in `src/tinylog/format.py` that maps a level string to an int "
        "rank, and wire it into `render_line` so lower-rank records can be "
        "filtered. Keep it stdlib-only and add a unit test in "
        "`tests/test_format.py`."
    )
    ids = b.assistant(
        "I'll read the current format module first.",
        [{"name": "Read", "input": {"file_path": "src/tinylog/format.py"}}],
    )
    b.tool_result(ids[0], "def render_line(record, scheme):\n    ...\n")
    ids = b.assistant(
        "Adding `parse_level` and wiring it into `render_line`.",
        [
            {
                "name": "Edit",
                "input": {
                    "file_path": "src/tinylog/format.py",
                    "old_string": "def render_line(record, scheme):",
                    "new_string": "def parse_level(level):\n    return _RANKS.get(level, 0)\n\n\ndef render_line(record, scheme):",
                },
            }
        ],
    )
    b.tool_result(ids[0], "Edit applied to src/tinylog/format.py")
    b.user("Now add the test for `parse_level` in `tests/test_format.py`.")
    ids = b.assistant(
        "Writing the test.",
        [
            {
                "name": "Write",
                "input": {
                    "file_path": "tests/test_format.py",
                    "content": "from tinylog.format import parse_level\n\n\ndef test_parse_level():\n    assert parse_level('error') > parse_level('info')\n",
                },
            }
        ],
    )
    b.tool_result(ids[0], "File written: tests/test_format.py")
    b.assistant("Done. `parse_level` is wired into `render_line` and tested.")
    b.user("yes, ship it")
    b.write("clean.jsonl")


def build_bloated() -> None:
    b = Builder("bloat000")
    # Cold start, >100 tokens, no brief line -> brief_miss.
    # Pastes SPEC_BLOCK once here...
    b.user(
        "I'm working on a structured logging CLI and need help with the line "
        "renderer. Here is the full format spec for reference, please keep it "
        "in mind for everything below:\n\n" + SPEC_BLOCK
    )
    b.assistant("Got it — I've read the spec. What would you like to change first?")
    # reexplain_over_tool: names a file + describes its contents at length.
    b.user(
        "The file src/tinylog/format.py contains the render_line function which "
        "takes a record dict and a ColorScheme, applies ANSI escape codes per "
        "severity level, pads the level name to five characters, formats the "
        "timestamp as ISO8601, joins all fields with a separator string, and "
        "returns the final rendered line. It also defines a helper _colorize "
        "that wraps text in escape codes and a module-level DEFAULT_SCHEME "
        "constant that the CLI imports at startup."
    )
    b.assistant("Understood. Which part should change?")
    # vague_prompt: <15 words, no anchor, not an ack.
    b.user("just fix it")
    b.assistant("Could you point me at the specific file or function?")
    # context_bloat: re-paste the identical SPEC_BLOCK verbatim.
    b.user("Here is the format spec again so you have it:\n\n" + SPEC_BLOCK)
    b.assistant("That spec was already in context — no need to re-send it.")
    b.write("bloated.jsonl")


def build_compacted() -> None:
    b = Builder("compact0")
    b.user("Run `tinylog brief`. Then refactor `validate_schema` in `src/tinylog/config.py`.")
    ids = b.assistant(
        "Reading the config module.",
        [{"name": "Read", "input": {"file_path": "src/tinylog/config.py"}}],
    )
    b.tool_result(
        ids[0],
        "def validate_schema(doc):\n    # checks required keys\n    ...\n",
    )
    b.assistant("`validate_schema` checks required keys against a schema map. Ready to refactor.")
    # ... long stretch of unrelated work would happen here ...
    b.compaction(pre_tokens=164000)
    # Post-compaction: references validate_schema again, no re-Read -> compaction_loss.
    b.user("Now make `validate_schema` also reject unknown keys, then run the tests.")
    b.assistant(
        "Updating validate_schema to reject unknown keys.",
        [
            {
                "name": "Edit",
                "input": {
                    "file_path": "src/tinylog/config.py",
                    "old_string": "    # checks required keys",
                    "new_string": "    # checks required keys and rejects unknown ones",
                },
            }
        ],
    )
    b.write("compacted.jsonl")


def main() -> None:
    build_clean()
    build_bloated()
    build_compacted()
    print("wrote clean.jsonl, bloated.jsonl, compacted.jsonl to", HERE)


if __name__ == "__main__":
    main()
