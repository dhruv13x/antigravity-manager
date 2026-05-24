
import pytest
from antigravity_manager.prune_backups import perform_prune_backups
from antigravity_manager.sync import push_backup, pull_backup
from antigravity_manager.restore import safe_extract
from antigravity_manager.backup import perform_backup

def test_prune_backups_cov2(tmp_path):
    # fully prune
    import json
    for i in range(5):
        p = tmp_path / f"test{i}-antigravity.tar.gz"
        p.touch()
        m = tmp_path / f"test{i}-antigravity.metadata.json"
        m.write_text(json.dumps({"email": f"a{i}@b.c", "captured_at": f"2023-01-0{i}T00:00:00"}))
    perform_prune_backups(tmp_path, keep=1, keep_latest_per_email=True, dry_run=False)

def test_sync_cov2(tmp_path, monkeypatch):
    import sys, types
    boto3_mock = types.ModuleType("boto3")
    client_mock = type('Client', (), {
        'head_bucket': lambda *a,**k: None,
        'upload_file': lambda *a,**k: None,
        'list_objects_v2': lambda *a,**k: {'Contents': [{'Key': 'x-antigravity.tar.gz'}, {'Key': 'y-antigravity.metadata.json'}]},
        'download_file': lambda *a,**k: None
    })
    boto3_mock.client = lambda *a,**k: client_mock()
    monkeypatch.setitem(sys.modules, "boto3", boto3_mock)

    (tmp_path / "x-antigravity.tar.gz").touch()
    (tmp_path / "y-antigravity.metadata.json").write_text('{}')

    from antigravity_manager.sync import push_backup, pull_backup
    push_backup(tmp_path, "b", "e", "a", "s", dry_run=False)
    pull_backup(tmp_path, "b", "e", "a", "s", dry_run=False)
