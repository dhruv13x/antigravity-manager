
import pytest
from antigravity_manager.cli import main
import sys
from pathlib import Path

def test_cli_status_no_file(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["agm", "status", "--input-file", "/nonexistent"])
    try: main()
    except SystemExit: pass

def test_cli_cooldown_json(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["agm", "cooldown", "--json"])
    monkeypatch.setattr("antigravity_manager.cli.list_backups", lambda *a,**k: [])
    monkeypatch.setattr("antigravity_manager.cli.evaluate_entries", lambda *a,**k: [])
    try: main()
    except SystemExit: pass

def test_cli_doctor_json(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["agm", "doctor", "--json"])
    monkeypatch.setattr("antigravity_manager.cli.run_doctor", lambda *a,**k: [])
    try: main()
    except SystemExit: pass

def test_cli_sync_no_direction(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["agm", "sync"])
    try: main()
    except SystemExit: pass

def test_backup_errors(monkeypatch, tmp_path):
    from antigravity_manager.backup import perform_backup
    import argparse
    monkeypatch.setattr("antigravity_manager.backup.get_status_for_backup", lambda a: None)
    args = argparse.Namespace(source_dir="/doesnotexist", gemini_home=str(tmp_path), backup_dir=str(tmp_path), dry_run=False)
    try: perform_backup(args)
    except FileNotFoundError: pass

def test_restore_errors(monkeypatch, tmp_path):
    from antigravity_manager.restore import perform_restore
    import argparse
    monkeypatch.setattr("antigravity_manager.restore.resolve_archive_path", lambda *a: Path("/doesnotexist"))
    args = argparse.Namespace(dest_dir=str(tmp_path), gemini_home=str(tmp_path))
    try: perform_restore(args)
    except FileNotFoundError: pass
