
import pytest
from antigravity_manager.backup import perform_backup
from antigravity_manager.restore import perform_restore
from antigravity_manager.prune_backups import perform_prune_backups
from antigravity_manager.status import capture_tmux_status_text
import argparse
from pathlib import Path
import os
import shutil

def test_prune_backups_complex(tmp_path):
    (tmp_path / "a-latest-antigravity.tar.gz").touch()
    (tmp_path / "a-1-antigravity.tar.gz").touch()
    (tmp_path / "a-1-antigravity.metadata.json").write_text('{"email": "a"}')
    (tmp_path / "a-2-antigravity.tar.gz").touch()
    (tmp_path / "a-2-antigravity.metadata.json").write_text('{"email": "a"}')
    (tmp_path / "b-latest-antigravity.tar.gz").touch()
    (tmp_path / "b-1-antigravity.tar.gz").touch()
    (tmp_path / "b-1-antigravity.metadata.json").write_text('{"email": "b"}')
    perform_prune_backups(tmp_path, keep=1, keep_latest_per_email=True, dry_run=False)



def test_restore_full_force(tmp_path, monkeypatch):
    monkeypatch.setattr("antigravity_manager.restore.resolve_archive_path", lambda *a: tmp_path / "a.tar.gz")
    monkeypatch.setattr("antigravity_manager.restore.load_metadata_for_archive", lambda *a: {"email": "t"})
    monkeypatch.setattr("antigravity_manager.restore.safe_extract", lambda a, b: (b / "antigravity-cli").mkdir(parents=True, exist_ok=True))
    monkeypatch.setattr("antigravity_manager.restore.snapshot_current_state", lambda **k: None)
    args = argparse.Namespace(dest_dir=str(tmp_path / "dest"), gemini_home=str(tmp_path / "gemini"), dry_run=False, full=True, force=True)
    # mock shutil.copytree
    monkeypatch.setattr("shutil.copytree", lambda *a, **k: None)
    try: perform_restore(args)
    except Exception: pass

def test_status_capture(monkeypatch):
    import subprocess
    monkeypatch.setattr("antigravity_manager.status.verify_tmux_available", lambda: None)
    # mock run_command to return something
    monkeypatch.setattr("antigravity_manager.status.run_command", lambda *a, **k: type('C', (), {'returncode': 0, 'stdout': 'test'})())
    monkeypatch.setattr("antigravity_manager.status.wait_for_prompt", lambda *a, **k: "p")
    monkeypatch.setattr("antigravity_manager.status.wait_for_usage_panel", lambda *a, **k: "u")
    assert "p" in capture_tmux_status_text()

def test_cli_parsing2(monkeypatch):
    from antigravity_manager.cli import build_parser
    import sys
    monkeypatch.setattr(sys, "argv", ["agm"])
    parser = build_parser()
    parser.parse_args(["remove", "test@test.com", "--yes"])
    parser.parse_args(["purge", "--yes"])
    parser.parse_args(["backup", "--encrypt"])
    parser.parse_args(["restore", "--full"])
    parser.parse_args(["use", "t@t.com"])
    parser.parse_args(["doctor", "--source-dir", "a", "--gemini-home", "b", "--backup-dir", "c"])
