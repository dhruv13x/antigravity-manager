from datetime import datetime
from pathlib import Path

import pytest

from antigravity_manager.backup import backup_result_to_text
from antigravity_manager.cooldown import CooldownStatus, print_statuses_table
from antigravity_manager.doctor import print_doctor_table
from antigravity_manager.list_backups import BackupEntry, print_entries_table
from antigravity_manager.prune import prune_result_to_text
from antigravity_manager.purge import purge_result_to_text
from antigravity_manager.remove import remove_result_to_text
from antigravity_manager.restore import restore_result_to_text
from antigravity_manager.status import LiveStatus, ModelQuotaStatus, live_status_to_text
from antigravity_manager.ui import banner, print_rich_help


def test_banner(capsys):
    banner()
    assert "M  A  N  A  G  E  R" in capsys.readouterr().out


def test_print_rich_help(capsys):
    with pytest.raises(SystemExit):
        print_rich_help()
    out = capsys.readouterr().out
    assert "Usage:" in out
    assert "Options" in out


def test_backup_result_to_text():
    panel = backup_result_to_text(
        Path("/archive"), Path("/meta"), {"email": "test@test.com"}, dry_run=False
    )
    assert panel is not None

    panel = backup_result_to_text(
        Path("/archive"), Path("/meta"), {"email": "test@test.com"}, dry_run=True
    )
    assert panel is not None


def test_restore_result_to_text():
    panel = restore_result_to_text(
        Path("/archive"), {}, [Path("/file1")], Path("/safety"), dry_run=False, full=True
    )
    assert panel is not None

    panel = restore_result_to_text(Path("/archive"), {}, [], None, dry_run=True, full=False)
    assert panel is not None


def test_prune_result_to_text():
    class MockPlan:
        def __init__(self):
            self.files = [Path("/f1")]
            self.directories = [Path("/d1")]

    panel = prune_result_to_text(MockPlan(), dry_run=False, source_dir=Path("/src"))
    assert panel is not None

    class MockPlanEmpty:
        def __init__(self):
            self.files = []
            self.directories = []

    panel = prune_result_to_text(MockPlanEmpty(), dry_run=True)
    assert panel is not None


def test_purge_result_to_text():
    panel = purge_result_to_text(True, source_dir=Path("/src"), dry_run=False)
    assert panel is not None

    panel = purge_result_to_text(False, source_dir=Path("/src"), dry_run=False)
    assert panel is not None


def test_remove_result_to_text():
    panel = remove_result_to_text(
        {"local_files_removed": ["/path"], "local_registry_removed": True},
        email="a@b.c",
        dry_run=False,
    )
    assert panel is not None

    panel = remove_result_to_text({}, email="a@b.c", dry_run=True)
    assert panel is not None


def test_live_status_to_text():
    model1 = ModelQuotaStatus(
        model_name="M1",
        quota_percent_left=100,
        is_available=True,
        refresh_in_text=None,
        refresh_at=None,
    )
    model2 = ModelQuotaStatus(
        model_name="M2",
        quota_percent_left=30,
        is_available=True,
        refresh_in_text=None,
        refresh_at=None,
    )
    model3 = ModelQuotaStatus(
        model_name="M3",
        quota_percent_left=5,
        is_available=True,
        refresh_in_text=None,
        refresh_at=None,
    )
    model4 = ModelQuotaStatus(
        model_name="M4",
        quota_percent_left=0,
        is_available=False,
        refresh_in_text="1h",
        refresh_at=datetime.now(),
    )
    model5 = ModelQuotaStatus(
        model_name="M5",
        quota_percent_left=None,
        is_available=True,
        refresh_in_text=None,
        refresh_at=None,
    )

    status = LiveStatus(
        email="t@t.com",
        plan="Pro",
        is_pro=True,
        captured_at=datetime.now(),
        models=(model1, model2, model3, model4, model5),
    )
    panel = live_status_to_text(status)
    assert panel is not None


def test_print_entries_table(capsys):
    print_entries_table([])
    out = capsys.readouterr().out
    assert "Antigravity Backups" in out

    entry = BackupEntry(Path("/a"), "a@b.c", "Pro", "auth", "now", "later", "auth-only", {})
    print_entries_table([entry])
    out = capsys.readouterr().out
    assert "a@b.c" in out


def test_print_statuses_table(capsys, monkeypatch):
    print_statuses_table([])
    out = capsys.readouterr().out
    assert "Antigravity Cooldown" in out

    monkeypatch.setattr("antigravity_manager.cooldown.read_active_email", lambda: "a@b.c")

    from antigravity_manager.cooldown import ModelCooldown

    m = ModelCooldown(
        name="m", quota_percent_left=100, is_available=True, refresh_at=None, remaining_seconds=0
    )
    s1 = CooldownStatus("a@b.c", "Pro", "ready", 1, 1, None, 0, "src", "dec", None, (m,))
    s2 = CooldownStatus("other", "Pro", "cooldown", 0, 1, None, 100, "src", "dec", None, (m,))
    s3 = CooldownStatus("other2", "Pro", "ready", 1, 1, None, 0, "src", "dec", None, (m,))

    print_statuses_table([s1, s2, s3])
    out = capsys.readouterr().out
    assert "ACTIVE" in out
    assert "COOLDOWN" in out
    assert "READY" in out


def test_print_doctor_table(capsys):
    print_doctor_table([("A", True, "ok"), ("B", False, "bad")])
    out = capsys.readouterr().out
    assert "OK" in out
    assert "FAIL" in out

    print_doctor_table([("A", True, "ok")])
    out = capsys.readouterr().out
    assert "OK" in out
