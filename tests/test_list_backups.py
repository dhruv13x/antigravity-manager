import json

from antigravity_manager.list_backups import build_backup_entry, list_backups


def test_list_backups_latest(tmp_path):
    bdir = tmp_path / "backups"
    bdir.mkdir()

    # 1
    p = bdir / "2024-01-01-user-antigravity.tar.gz"
    p.touch()
    (bdir / "2024-01-01-user-antigravity.metadata.json").write_text(
        json.dumps(
            {
                "email": "user",
                "captured_at": "2024-01-01T00:00:00",
                "created_at": "2024-01-01T00:00:00",
                "source": "test",
                "product": "antigravity",
            }
        )
    )

    entries = list_backups(bdir, email="user", latest_per_email=False)
    assert len(entries) == 1
    assert entries[0].email == "user"

    entries2 = list_backups(bdir, email="user", latest_per_email=True)
    assert len(entries2) == 1


def test_build_backup_entry(tmp_path):
    bdir = tmp_path / "backups"
    bdir.mkdir()
    p = bdir / "1-a-antigravity.tar.gz"
    p.touch()
    (bdir / "1-a-antigravity.metadata.json").write_text(
        json.dumps({"email": "a", "captured_at": "2024-01-01T00:00:00", "product": "antigravity"})
    )
    ent = build_backup_entry(p)
    assert ent.email == "a"


def test_build_backup_entry_fail(tmp_path):
    bdir = tmp_path / "backups"
    bdir.mkdir()
    p = bdir / "1-a-antigravity.tar.gz"
    p.touch()
    ent = build_backup_entry(p)
    assert ent is None
