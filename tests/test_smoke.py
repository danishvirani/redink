"""Smoke tests for the v0.0 scaffold.

These pass before any real audit logic exists. They verify:
- The package imports
- argparse renders --help correctly
- `version` command works
- Stub commands exit non-zero with a clear "not yet implemented" message
"""

import io
from contextlib import redirect_stderr, redirect_stdout

import pytest

import redink
from redink import cli


def test_version_constant():
    assert redink.__version__ == "0.0.1"


def test_help_renders_with_commands():
    parser = cli.build_parser()
    captured = io.StringIO()
    with redirect_stdout(captured):
        with pytest.raises(SystemExit) as exc:
            parser.parse_args(["--help"])
        assert exc.value.code == 0
    out = captured.getvalue()
    assert "redink" in out
    assert "watch" in out
    assert "audit" in out
    assert "export" in out
    assert "version" in out


def test_version_command_prints_and_returns_zero():
    captured = io.StringIO()
    with redirect_stdout(captured):
        rc = cli.main(["version"])
    assert rc == 0
    assert "redink 0.0.1" in captured.getvalue()


def test_audit_missing_session_returns_nonzero():
    captured = io.StringIO()
    with redirect_stderr(captured):
        rc = cli.main(["audit", "/tmp/does-not-exist-redink.jsonl"])
    assert rc == 1
    err = captured.getvalue()
    assert "redink:" in err
    assert "not found" in err


def test_export_stub_returns_nonzero():
    captured = io.StringIO()
    with redirect_stderr(captured):
        rc = cli.main(["export", "/tmp/dummy.jsonl"])
    assert rc == 1
    assert "not yet implemented" in captured.getvalue()


def test_watch_stub_returns_nonzero():
    captured = io.StringIO()
    with redirect_stderr(captured):
        rc = cli.main(["watch"])
    assert rc == 1
    err = captured.getvalue()
    assert "not yet implemented" in err
    assert "8787" in err


def test_watch_accepts_port_flag():
    captured = io.StringIO()
    with redirect_stderr(captured):
        rc = cli.main(["watch", "--port", "9000"])
    assert rc == 1
    assert "9000" in captured.getvalue()


def test_no_subcommand_errors_cleanly():
    captured = io.StringIO()
    with redirect_stderr(captured):
        with pytest.raises(SystemExit) as exc:
            cli.main([])
        assert exc.value.code != 0
