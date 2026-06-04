"""Tests for the wired `redink audit` command."""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from redink import cli
from redink.errors import RedinkError

FIXTURES = Path(__file__).parent / "fixtures" / "sessions"


def test_audit_a_fixture_prints_report_and_returns_zero():
    out = io.StringIO()
    with redirect_stdout(out):
        rc = cli.main(["audit", str(FIXTURES / "bloated.jsonl")])
    assert rc == 0
    text = out.getvalue()
    assert "redink audit" in text
    assert "Score  56/100" in text
    assert "context_bloat" in text


def test_audit_clean_fixture_is_clean():
    out = io.StringIO()
    with redirect_stdout(out):
        rc = cli.main(["audit", str(FIXTURES / "clean.jsonl")])
    assert rc == 0
    assert "No anti-patterns detected" in out.getvalue()


def test_resolve_directory_picks_latest_session(tmp_path: Path):
    old = tmp_path / "old.jsonl"
    new = tmp_path / "new.jsonl"
    old.write_text('{"type":"user","message":{"role":"user","content":"a"}}\n')
    new.write_text('{"type":"user","message":{"role":"user","content":"b"}}\n')
    import os

    os.utime(old, (1, 1))
    os.utime(new, (2, 2))
    assert cli.resolve_session_path(str(tmp_path)) == new


def test_resolve_current_project_uses_encoded_dir(tmp_path: Path, monkeypatch):
    projects = tmp_path / "projects"
    encoded = projects / cli._encode_project_dir(Path.cwd())
    encoded.mkdir(parents=True)
    session = encoded / "s.jsonl"
    session.write_text('{"type":"user","message":{"role":"user","content":"x"}}\n')
    assert cli.resolve_session_path(None, projects_dir=projects) == session


def test_resolve_missing_project_raises(tmp_path: Path):
    with pytest.raises(RedinkError, match="no Claude Code sessions"):
        cli.resolve_session_path(None, projects_dir=tmp_path / "empty")
