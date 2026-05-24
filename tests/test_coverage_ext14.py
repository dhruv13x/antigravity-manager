
import pytest
import argparse
from pathlib import Path
from antigravity_manager.sync import *
from antigravity_manager.restore import *
from antigravity_manager.credentials import *
from antigravity_manager.cli import *
from antigravity_manager.prune_backups import *
import sys

def test_sync_branches(monkeypatch, tmp_path):
    import sys, types
    boto3_mock = types.ModuleType("boto3")
    client_mock = type('Client', (), {
        'head_bucket': lambda *a,**k: None,
        'upload_file': lambda *a,**k: None,
        'list_objects_v2': lambda *a,**k: {'Contents': [{'Key': 'x'}]},
        'download_file': lambda *a,**k: None
    })
    boto3_mock.client = lambda *a,**k: client_mock()
    monkeypatch.setitem(sys.modules, "boto3", boto3_mock)

    args = argparse.Namespace(direction="pull", backup_dir=str(tmp_path), dry_run=False, access_key="a", secret_key="b", bucket_name="c", endpoint_url=None)
    monkeypatch.setattr(sys, "argv", ["agm", "sync"])
    # Just to get cli coverage
    monkeypatch.setattr("antigravity_manager.cli.resolve_credentials", lambda *a: ("a", "b", "c", None))
    handle_sync(args)

    args = argparse.Namespace(direction="push", backup_dir=str(tmp_path), dry_run=False, access_key="a", secret_key="b", bucket_name="c", endpoint_url=None)
    handle_sync(args)

def test_restore_branches_2(monkeypatch, tmp_path):
    monkeypatch.setattr("antigravity_manager.restore.resolve_archive_path", lambda *a,**k: tmp_path/"a")
    monkeypatch.setattr("antigravity_manager.restore.load_metadata_for_archive", lambda *a: {"email": "t"})
    monkeypatch.setattr("antigravity_manager.restore.safe_extract", lambda *a,**k: None)
    monkeypatch.setattr("antigravity_manager.restore.snapshot_current_state", lambda **k: None)
    monkeypatch.setattr("antigravity_manager.restore.restore_full", lambda *a,**k: None)

    args = argparse.Namespace(dest_dir=str(tmp_path), gemini_home=str(tmp_path), from_archive=str(tmp_path/"a"), dry_run=False, full=False, force=False)
    # mock restore_auth_only
    monkeypatch.setattr("antigravity_manager.restore.restore_auth_only", lambda *a,**k: [])
    perform_restore(args)

    args.full = True
    perform_restore(args)

def test_prune_backups_clean(monkeypatch, tmp_path):
    (tmp_path / "x-antigravity.tar.gz").touch()
    perform_prune_backups(tmp_path, keep=0, keep_latest_per_email=False, dry_run=True)

def test_cli_misc(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["agm", "unknown_cmd"])
    try: main()
    except SystemExit: pass
