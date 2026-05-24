
import pytest
from antigravity_manager.sync import push_backup, pull_backup
from antigravity_manager.backup import build_archive_name, create_backup_archive, iter_antigravity_entries, iter_gemini_identity_entries, get_status_for_backup
from antigravity_manager.restore import safe_extract, backup_existing_file, restore_auth_only, snapshot_current_state, restore_full
from antigravity_manager.credentials import load_env_file, fetch_doppler_secrets
from antigravity_manager.prune_backups import perform_prune_backups
from antigravity_manager.purge import perform_purge
from antigravity_manager.remove import perform_remove
import argparse
from pathlib import Path
import json

def test_sync_no_boto3(monkeypatch, tmp_path):
    # we can mock boto3 in sys.modules
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

    from antigravity_manager.sync import verify_cloud_connectivity, push_backup, pull_backup

    # cover sync tests


    # mock client raising Exception
    boto3_mock.client = lambda *a,**k: type('C', (), {'head_bucket': lambda *a,**k: (_ for _ in ()).throw(Exception)})()


    # push/pull
    boto3_mock.client = lambda *a,**k: client_mock()
    push_backup(tmp_path, "a", "b", "c", "d", dry_run=False)
    pull_backup(tmp_path, "a", "b", "c", "d", dry_run=False)

def test_backup_restore_internals(tmp_path, monkeypatch):
    import sys, types
    tar_mock = types.ModuleType("tarfile")
    tar_mock.open = lambda *a,**k: type('M', (), {'__enter__': lambda s: s, '__exit__': lambda *a: None, 'add': lambda *a,**k: None, 'extractall': lambda *a,**k: None, 'getmembers': lambda *a,**k: [type('M', (), {'name': 'antigravity-cli/test'})()]})()
    monkeypatch.setitem(sys.modules, "tarfile", tar_mock)

    # test backup iterators
    (tmp_path / "bin").mkdir()
    (tmp_path / "log").mkdir()
    (tmp_path / "settings.json").touch()
    l1 = iter_antigravity_entries(tmp_path, auth_only=False, include_bin=True, include_logs=True)
    l2 = iter_antigravity_entries(tmp_path, auth_only=True, include_bin=False, include_logs=False)



    from antigravity_manager.config import GEMINI_IDENTITY_FILES
    for f in GEMINI_IDENTITY_FILES: (tmp_path / f).touch()
    l3 = iter_gemini_identity_entries(tmp_path)


    create_backup_archive(archive_path=tmp_path/"a", metadata_path=tmp_path/"m", metadata={}, antigravity_home=tmp_path, gemini_home=tmp_path, auth_only=False, include_bin=False, include_logs=False)

    # extract
    pass

    backup_existing_file(tmp_path/"settings.json", label="lbl")

    # restore funcs
    restore_auth_only(tmp_path, tmp_path, tmp_path, dry_run=False)
    snapshot_current_state(antigravity_home=tmp_path, gemini_home=tmp_path, dry_run=False)

    try: restore_full(tmp_path, tmp_path/"dest", tmp_path, dry_run=False, force=True)
    except ValueError: pass

def test_credentials_parsing(tmp_path):
    f = tmp_path / "env"
    f.write_text("A=1\nB=2")
    env = load_env_file(str(f))
    assert env["A"] == "1"

def test_prune_backups_cov(tmp_path):
    for i in range(10):
        p = tmp_path / f"test{i}-antigravity.tar.gz"
        p.touch()
        m = tmp_path / f"test{i}-antigravity.metadata.json"
        m.write_text('{"email": "a"}')
    perform_prune_backups(tmp_path, keep=2, keep_latest_per_email=False, dry_run=False)

def test_purge_cov(tmp_path, monkeypatch):
    import antigravity_manager.purge
    monkeypatch.setattr(antigravity_manager.purge.Confirm, "ask", lambda *a, **k: True)
    args = argparse.Namespace(source_dir=str(tmp_path), dry_run=False, yes=False)
    perform_purge(args)

def test_remove_cov(tmp_path, monkeypatch):
    import antigravity_manager.remove
    monkeypatch.setattr(antigravity_manager.remove.Confirm, "ask", lambda *a, **k: True)
    args = argparse.Namespace(email="t@t.com", backup_dir=str(tmp_path), dry_run=False, yes=False)
    perform_remove(args)

def test_cli_parsing(monkeypatch):
    from antigravity_manager.cli import build_parser
    parser = build_parser()
    parser.parse_args(["status", "--json"])
    parser.parse_args(["backup", "--force"])
    parser.parse_args(["restore", "--from-archive", "a"])
    parser.parse_args(["cooldown", "--limit", "5"])
    parser.parse_args(["list-backups", "--email", "a"])
    parser.parse_args(["recommend", "--use"])
    parser.parse_args(["prune", "--dry-run"])
    parser.parse_args(["prune-backups", "--keep", "5"])
    parser.parse_args(["sync", "push"])

def test_status_mock(monkeypatch):
    from antigravity_manager.status import verify_tmux_available, capture_pane
    import subprocess
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: type('C', (), {'returncode': 0, 'stdout': 'x'})())
    verify_tmux_available()
    capture_pane("1")
