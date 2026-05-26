import json
from pathlib import Path
from antigravity_manager.prune_backups import perform_prune_backups

def test_prune_backups_consolidated(tmp_path):
    bdir = tmp_path / "backups"
    bdir.mkdir()
    
    # 1. Create 2 backups for user1
    for stamp in ["2026-05-25T10:00:00Z", "2026-05-26T10:00:00Z"]:
        safe = stamp.replace(":", "").replace("-", "")[:15]
        archive = bdir / f"{safe}-user1@example.com-antigravity.tar.gz"
        archive.touch()
        meta = bdir / f"{safe}-user1@example.com-antigravity.metadata.json"
        meta.write_text(json.dumps({
            "product": "antigravity",
            "email": "user1@example.com",
            "created_at": stamp,
            "captured_at": stamp,
            "archive_name": archive.name
        }))

    # 2. Create 2 status events for user1
    status_dir = bdir / "status" / "events"
    status_dir.mkdir(parents=True)
    for stamp in ["2026-05-25T11:00:00Z", "2026-05-26T11:00:00Z"]:
        safe = stamp.replace(":", "").replace("-", "")[:15]
        status_file = status_dir / f"status__email_user1_example_com__checked_{safe}.json"
        status_file.write_text(json.dumps({
            "product": "antigravity",
            "record_type": "status",
            "email": "user1@example.com",
            "created_at": stamp,
            "captured_at": stamp
        }))

    # Prune keeping only 1 of each
    deleted = perform_prune_backups(bdir, keep=1, dry_run=False)
    
    # Verify backup pruning
    assert (bdir / "20260526T100000-user1@example.com-antigravity.tar.gz").exists()
    assert (bdir / "20260526T100000-user1@example.com-antigravity.metadata.json").exists()
    assert not (bdir / "20260525T100000-user1@example.com-antigravity.tar.gz").exists()
    assert not (bdir / "20260525T100000-user1@example.com-antigravity.metadata.json").exists()
    
    # Verify status pruning
    assert (status_dir / "status__email_user1_example_com__checked_20260526T110000.json").exists()
    assert not (status_dir / "status__email_user1_example_com__checked_20260525T110000.json").exists()
    
    deleted_names = [p.name for p in deleted]
    assert "20260525T100000-user1@example.com-antigravity.tar.gz" in deleted_names
    assert "20260525T100000-user1@example.com-antigravity.metadata.json" in deleted_names
    assert "status__email_user1_example_com__checked_20260525T110000.json" in deleted_names
    assert len(deleted) == 3
