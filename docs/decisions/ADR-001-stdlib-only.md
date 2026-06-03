# ADR-001: redink is stdlib-only

Date: 2026-06-03
Status: Accepted
Deciders: Danish Virani

## Context

redink is a CLI that reads local AI session logs (JSON Lines from Claude Code, SQLite from Cursor) and emits opinionated audits. It runs on a developer's laptop. No network calls in v0.1; the LLM-aided rule explanations in v0.2+ may call an LLM API.

There are two obvious dependency stacks:

**Option A — pick reasonable libraries.** `rich` for terminal output, `pydantic` for parsing session JSON, `httpx` for any future API calls, `click` for the CLI surface, maybe `watchdog` for filesystem watching. Roughly the default Python stack of 2026.

**Option B — Python standard library only.** `argparse` + `json` + `sqlite3` + `urllib` + `re` + ANSI escape codes for color. `os.scandir` polling for filesystem watching.

The AI tooling space in 2026 favors Option A. Median install command for a competing audit tool is roughly:

```
pip install langchain pydantic-settings rich click typer chromadb
```

I want redink to install with:

```
curl -fsSL .../install.sh | sh
```

The install command is the first user experience and most AI tooling fails it on day one.

## Decision

**Option B. Stdlib only at runtime. Zero runtime dependencies.**

Test/lint tooling (`pytest`, `ruff`) is fine — it never runs on a user's machine.

## Consequences

**Good:**

1. Install stays one shell line forever. The pitch IS the install command.
2. Cold start is Python's interpreter startup (~30ms on a modern Mac). No library imports, no pydantic model compilation.
3. Zero attack surface beyond stdlib. No transitive vulnerability headaches.
4. Forces design discipline. Want `pydantic`? Write five lines of `json.loads` + a `@dataclass`. Want `httpx`? `urllib.request.urlopen` with an explicit timeout. Want `rich`? Define ANSI escape constants.
5. The Python you already have is the Python that runs. Any 3.10+ works. No version pinning hell.

**Bad — accepted openly:**

1. ANSI escape rendering is uglier than `rich`. The red ✗ + green ✓ + dim gray we need is ~25 lines of constants. We live with it.
2. argparse error messages aren't as polished as `click`. Live with it.
3. Some inner code is more verbose than it would be with the right library. Verbosity is the price of the install command.
4. JSON parse error messages aren't as friendly as pydantic's. We funnel them through `RedinkError` with the first 300 chars of the offending input.
5. Filesystem watching via polling (every 250ms) burns slightly more CPU than `watchdog`'s inotify-style. v0.3 problem; v0.1 doesn't need it.

## Alternatives considered

**"One dep is fine — just `rich`."** Terminal output IS the user surface and `rich` is small + maintained. But:

- Once one dep ships, the second is psychologically free. The line moves.
- `pip install rich` requires `pip` on the user's box, which philosophically defeats the curl-install pitch even if `pipx install redink` technically works.
- The ANSI escape constants we actually need (red ✗, green ✓, dim gray, bold, reset) are 25 lines. Not worth a dep.

Rejected.

**"Vendor `rich` into `src/redink/_vendor/`."** Considered — it's what pip itself does with requests. Rejected because the v0.0 curl-install ships a single Python file launcher; vendoring breaks the single-file model. Future ADR could revisit if curl-install is restructured.

**"Use `tiktoken` for accurate token counting."** Tempting for the context-bloat rule. Rejected v0.1: it adds a compiled C extension, breaks the "any Python 3.10+ works" promise, and the heuristic (4 chars ≈ 1 token for English code-mixed content) is close enough to flag the egregious cases that matter. Document the imprecision in `docs/rules/context-bloat.md`.

## When this is wrong

This ADR is superseded if:

- A critical capability requires a dep we can't reasonably implement in stdlib (e.g., a session format moves to gRPC or Protobuf). Write ADR-00N to take a single justified dep.
- Performance becomes the user complaint. We add deps for correctness, not for cosmetics.
- Vendor SDKs become the only path to a critical backend feature.

## How we'll know this was right

- Within 3 months: at least one external user writes "I love that this just installs." That comment is the validation.
- Within 6 months: no runtime dependency has been added. If we did, this ADR is superseded by ADR-00N.

## References

- Simon Willison's `llm` CLI — closest spiritual predecessor, similar stdlib-leaning discipline.
- Mitchell Hashimoto on Ghostty — ship what works, treat the install as a feature.
- The Python stdlib documentation, which is better than people remember.
