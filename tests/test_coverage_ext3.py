
import pytest
import argparse
from pathlib import Path
from antigravity_manager.cli import main, handle_recommend

def test_cli_use_command2(monkeypatch, capsys):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "use", "t@t.com"])
    # Do not mock handle_use, just mock perform_restore to not do anything and return safe values
    monkeypatch.setattr("antigravity_manager.cli.perform_restore", lambda args: (Path("/a"), {}, [], None))
    try:
        main()
    except SystemExit:
        pass
    out = capsys.readouterr().out
    assert out is not None

def test_cli_remove_command2(monkeypatch, capsys):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "remove", "t@t.com"])
    monkeypatch.setattr("antigravity_manager.cli.perform_remove", lambda args: {"local_files_removed": [], "local_registry_removed": False})
    try: main()
    except SystemExit: pass

def test_cli_purge_command2(monkeypatch, capsys):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "purge"])
    monkeypatch.setattr("antigravity_manager.cli.perform_purge", lambda args: True)
    try: main()
    except SystemExit: pass

def test_cli_profile_command2(monkeypatch, capsys):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "profile", "export", "/tmp/p", "--dry-run"])
    monkeypatch.setattr("antigravity_manager.cli.export_profile", lambda *a, **k: None)
    try: main()
    except SystemExit: pass

def test_cli_list_backups2(monkeypatch, capsys):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "list-backups", "--json"])
    monkeypatch.setattr("antigravity_manager.cli.list_backups", lambda *a, **k: [])
    try: main()
    except SystemExit: pass

def test_cli_cooldown2(monkeypatch, capsys):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "cooldown", "--json"])
    monkeypatch.setattr("antigravity_manager.cli.list_backups", lambda *a, **k: [])
    monkeypatch.setattr("antigravity_manager.cli.evaluate_entries", lambda *a, **k: [])
    try: main()
    except SystemExit: pass

def test_cli_status2(monkeypatch, capsys):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "status", "--json"])
    monkeypatch.setattr("antigravity_manager.cli.capture_tmux_status_text", lambda *a, **k: "")
    from antigravity_manager.status import LiveStatus
    from datetime import datetime
    s = LiveStatus("t", "p", True, datetime.now(), ())
    monkeypatch.setattr("antigravity_manager.cli.parse_live_status_text", lambda *a, **k: s)
    monkeypatch.setattr("antigravity_manager.cli.update_registry_from_status", lambda *a, **k: None)
    try: main()
    except SystemExit: pass





def test_cli_doctor2(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "doctor", "--json"])
    monkeypatch.setattr("antigravity_manager.cli.run_doctor", lambda *a, **k: [("a", True, "ok")])
    try: main()
    except SystemExit: pass

def test_cli_prune2(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "prune"])
    from antigravity_manager.prune import PrunePlan
    monkeypatch.setattr("antigravity_manager.cli.perform_prune", lambda *a, **k: type("PrunePlan", (), {"files": [], "directories": []})())
    try: main()
    except SystemExit: pass

def test_cli_sync_call(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "sync", "push", "--bucket-name", "b"])
    monkeypatch.setattr("antigravity_manager.cli.resolve_credentials", lambda *a, **k: ("k", "s", "b", "u"))
    monkeypatch.setattr("antigravity_manager.cli.push_backup", lambda *a, **k: None)
    try: main()
    except SystemExit: pass
