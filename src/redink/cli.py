"""redink CLI entry point.

v0.0: the CLI surface is wired but the audit and export engines are stubs.
v0.1 ships the real audit engine. See docs/roadmap.md.
"""

import argparse
import re
import sys
from pathlib import Path

from redink import __version__
from redink.errors import RedinkError
from redink.parser import parse_file
from redink.report import render, should_color
from redink.rules import run_all
from redink.score import score_session


def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr)


def cmd_version(args: argparse.Namespace) -> int:
    print(f"redink {__version__}")
    return 0


def _encode_project_dir(path: Path) -> str:
    """Claude Code stores a project's sessions under a path-derived dir name,
    with every non-alphanumeric char replaced by a dash."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def _latest_session_in(directory: Path) -> Path:
    sessions = sorted(directory.glob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not sessions:
        raise RedinkError(f"no .jsonl sessions found in {directory}")
    return sessions[0]


def resolve_session_path(arg: str | None, projects_dir: Path | None = None) -> Path:
    """Turn the audit argument into a concrete session file.

    A file path is used as-is; a directory resolves to its most recent session;
    nothing resolves to the most recent session of the current project.
    """
    if arg:
        path = Path(arg).expanduser()
        return _latest_session_in(path) if path.is_dir() else path

    base = projects_dir or (Path.home() / ".claude" / "projects")
    project = base / _encode_project_dir(Path.cwd())
    if not project.is_dir():
        raise RedinkError(
            "no Claude Code sessions found for this project "
            f"({project}). Pass a session path explicitly."
        )
    return _latest_session_in(project)


def cmd_audit(args: argparse.Namespace) -> int:
    try:
        path = resolve_session_path(args.path)
        session = parse_file(path)
        score = score_session(run_all(session))
        sys.stdout.write(render(session, score, color=should_color()))
    except RedinkError as exc:
        _eprint(f"redink: {exc}")
        return 1
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    _eprint(f"redink: export not yet implemented (target: {args.path})")
    _eprint("v0.1 ships the self-contained HTML export.")
    _eprint("See docs/roadmap.md for the build sequence.")
    return 1


def cmd_watch(args: argparse.Namespace) -> int:
    _eprint(f"redink: watch not yet implemented (would listen on :{args.port})")
    _eprint("v0.1 ships the live web UI. This is the lede.")
    _eprint("See docs/roadmap.md and docs/sessions/track-b-visualizer.md.")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="redink",
        description="Watch your Claude Code session live, with red ink in the margins.",
        epilog="Full docs at https://github.com/danishvirani/redink",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    p_watch = sub.add_parser(
        "watch",
        help="Start the live web UI and watch sessions as they happen",
    )
    p_watch.add_argument(
        "--port",
        type=int,
        default=8787,
        help="Port to bind the local web UI (default: 8787)",
    )
    p_watch.add_argument(
        "--projects-dir",
        default=None,
        help="Path to ~/.claude/projects/ (defaults to that)",
    )
    p_watch.set_defaults(func=cmd_watch)

    p_audit = sub.add_parser(
        "audit",
        help="Run the audit post-hoc and print a marked-up terminal report",
    )
    p_audit.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Path to a session JSONL file or project directory (defaults to current project)",
    )
    p_audit.set_defaults(func=cmd_audit)

    p_export = sub.add_parser(
        "export",
        help="Export a session audit as a shareable, self-contained HTML report",
    )
    p_export.add_argument("path", help="Path to a session JSONL file")
    p_export.set_defaults(func=cmd_export)

    p_version = sub.add_parser("version", help="Print redink version")
    p_version.set_defaults(func=cmd_version)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
