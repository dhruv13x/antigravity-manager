
import pytest
from antigravity_manager.cli import main
from antigravity_manager.ui import print_rich_help

def test_cli_all_commands(monkeypatch):
    import sys
    cmds = [
        ("backup", "handle_backup"),
        ("restore", "handle_restore"),
        ("sync", "handle_sync"),
        ("check-cloud", "handle_check_cloud"),
        ("profile", "handle_profile"),
        ("purge", "handle_purge"),
        ("prune", "handle_prune"),
        ("prune-backups", "handle_prune_backups"),
        ("remove", "handle_remove"),
        ("doctor", "handle_doctor"),
        ("list-backups", "handle_list_backups"),
        ("cooldown", "handle_cooldown"),
        ("status", "handle_status"),
        ("recommend", "handle_recommend"),
        ("use", "handle_use")
    ]
    for cmd, handler in cmds:
        monkeypatch.setattr(sys, "argv", ["agm", cmd])
        monkeypatch.setattr(f"antigravity_manager.cli.{handler}", lambda *a, **k: None)
        try: main()
        except SystemExit: pass

def test_cli_options(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "--help"])
    monkeypatch.setattr("antigravity_manager.cli.print_rich_help", lambda: None)
    monkeypatch.setattr("antigravity_manager.cli.banner", lambda: None)
    try: main()
    except SystemExit: pass
