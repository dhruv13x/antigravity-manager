import json

from antigravity_manager.cli import handle_list_backups
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
