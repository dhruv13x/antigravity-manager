import json

from antigravity_manager.cli import handle_list_backups
from antigravity_manager.list_backups import (
    build_backup_entry,
    list_backups,
    list_status_metadata,
)


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


def test_cli_list_backups_defaults_latest_and_all_flag(tmp_path, capsys):
    bdir = tmp_path / "backups"
    bdir.mkdir()

    for stamp, email in [
        ("2024-01-01", "user@example.com"),
        ("2024-01-02", "user@example.com"),
        ("2024-01-03", "other@example.com"),
    ]:
        archive = bdir / f"{stamp}-{email}-antigravity.tar.gz"
        archive.touch()
        archive.with_name(archive.name.replace(".tar.gz", ".metadata.json")).write_text(
            json.dumps(
                {
                    "email": email,
                    "captured_at": f"{stamp}T00:00:00",
                    "created_at": f"{stamp}T00:00:00",
                    "product": "antigravity",
                }
            ),
            encoding="utf-8",
        )

    class Args:
        backup_dir = str(bdir)
        email = None
        json = False
        all = False

    handle_list_backups(Args())
    out = capsys.readouterr().out
    assert "2024-01-02" in out
    assert "2024-01-03" in out
    assert "2024-01-01" not in out

    Args.all = True
    handle_list_backups(Args())
    out = capsys.readouterr().out
    assert "2024-01-01" in out
    assert "2024-01-02" in out
    assert "2024-01-03" in out


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


def test_list_status_metadata_latest_per_email(tmp_path):
    bdir = tmp_path / "backups"
    bdir.mkdir()

    for stamp, email in [
        ("2024-01-01T00:00:00+00:00", "user@example.com"),
        ("2024-01-02T00:00:00+00:00", "user@example.com"),
        ("2024-01-03T00:00:00+00:00", "other@example.com"),
    ]:
        safe_stamp = stamp.replace(":", "").replace("+", "")
        (bdir / f"{safe_stamp}-{email}-antigravity.status.metadata.json").write_text(
            json.dumps(
                {
                    "record_type": "status",
                    "email": email,
                    "captured_at": stamp,
                    "created_at": stamp,
                    "backup_mode": "status-only",
                    "product": "antigravity",
                    "status": {"models": []},
                }
            ),
            encoding="utf-8",
        )

    entries = list_status_metadata(bdir, latest_per_email=True)

    assert len(entries) == 2
    assert entries[0].email == "other@example.com"
    user_entry = next(entry for entry in entries if entry.email == "user@example.com")
    assert user_entry.captured_at == "2024-01-02T00:00:00+00:00"
    assert user_entry.source == "status"
