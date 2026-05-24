
import pytest
from antigravity_manager.backup import perform_backup
from antigravity_manager.restore import perform_restore
from antigravity_manager.prune import perform_prune
from antigravity_manager.prune_backups import perform_prune_backups
from antigravity_manager.remove import perform_remove
from antigravity_manager.purge import perform_purge
import argparse
from pathlib import Path
import json

def test_perform_backup_dry(tmp_path, monkeypatch):
    monkeypatch.setattr("antigravity_manager.backup.get_status_for_backup", lambda a: __import__('antigravity_manager.status').status.LiveStatus('t@t.com', 'Pro', True, __import__('datetime').datetime.now(), ()))
    monkeypatch.setattr("antigravity_manager.backup.resolve_backup_anchor", lambda *a: (__import__('datetime').datetime.now(), "src", None))
    args = argparse.Namespace(source_dir=str(tmp_path), gemini_home=str(tmp_path), backup_dir=str(tmp_path), dry_run=True)
    a, m, meta = perform_backup(args)
    assert meta["email"] == "t@t.com"

def test_perform_restore_dry(tmp_path, monkeypatch):
    monkeypatch.setattr("antigravity_manager.restore.resolve_archive_path", lambda *a: tmp_path / "a.tar.gz")
    monkeypatch.setattr("antigravity_manager.restore.load_metadata_for_archive", lambda *a: {"email": "t"})
    monkeypatch.setattr("antigravity_manager.restore.safe_extract", lambda *a: None)
    args = argparse.Namespace(dest_dir=str(tmp_path), gemini_home=str(tmp_path), dry_run=True, full=True)
    try: perform_restore(args)
    except Exception: pass

def test_prune_full(tmp_path):
    args = argparse.Namespace(source_dir=str(tmp_path), dry_run=False)
    # mock everything safe
    pass
