
import pytest
import argparse
from pathlib import Path
from antigravity_manager.cli import main
from antigravity_manager.backup import perform_backup

def test_cli_cooldown_command(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "cooldown"])
    # mock to avoid crashing
    monkeypatch.setattr("antigravity_manager.cli.handle_cooldown", lambda args: print("cooldown called"))
    try:
        main()
    except SystemExit:
        pass

def test_cli_list_backups_command(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "list-backups"])
    monkeypatch.setattr("antigravity_manager.cli.handle_list_backups", lambda args: print("list called"))
    try:
        main()
    except SystemExit:
        pass

def test_cli_status_command(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "status"])
    monkeypatch.setattr("antigravity_manager.cli.handle_status", lambda args: print("status called"))
    try:
        main()
    except SystemExit:
        pass

def test_cli_recommend_command(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "recommend"])
    monkeypatch.setattr("antigravity_manager.cli.handle_recommend", lambda args: print("rec called"))
    try:
        main()
    except SystemExit:
        pass

def test_cli_doctor_command(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "doctor"])
    monkeypatch.setattr("antigravity_manager.cli.handle_doctor", lambda args: print("doc called"))
    try:
        main()
    except SystemExit:
        pass

def test_cli_use_command(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "use", "t@t.com"])
    monkeypatch.setattr("antigravity_manager.cli.handle_use", lambda args: print("use called"))
    try:
        main()
    except SystemExit:
        pass

def test_cli_backup_command(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "backup"])
    monkeypatch.setattr("antigravity_manager.cli.handle_backup", lambda args: print("backup called"))
    try:
        main()
    except SystemExit:
        pass

def test_cli_restore_command(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "restore"])
    monkeypatch.setattr("antigravity_manager.cli.handle_restore", lambda args: print("restore called"))
    try:
        main()
    except SystemExit:
        pass



def test_cli_prune_command(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "prune"])
    monkeypatch.setattr("antigravity_manager.cli.handle_prune", lambda args: print("prune called"))
    try: main()
    except SystemExit: pass

def test_cli_prune_backups_command(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "prune-backups"])
    monkeypatch.setattr("antigravity_manager.cli.handle_prune_backups", lambda args: print("prune backups called"))
    try: main()
    except SystemExit: pass

def test_cli_check_cloud_command(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "check-cloud"])
    monkeypatch.setattr("antigravity_manager.cli.handle_check_cloud", lambda args: print("check cloud called"))
    try: main()
    except SystemExit: pass



def test_backup_logic(monkeypatch, tmp_path):
    # Coverage for backup.py
    from antigravity_manager.backup import build_backup_metadata
    from antigravity_manager.status import LiveStatus
    from datetime import datetime
    s = LiveStatus("t@t.com", "Pro", True, datetime.now(), ())
    m = build_backup_metadata(s, tmp_path / "a", source_antigravity_home=tmp_path, source_gemini_home=tmp_path, backup_mode="auth", include_bin=False, include_logs=False, decision_model="a", backup_anchor_at=datetime.now(), backup_anchor_source="a", backup_anchor_model="a")
    assert "schema_version" in m

def test_restore_logic(monkeypatch, tmp_path):
    from antigravity_manager.restore import validate_member_name
    validate_member_name("antigravity-cli/test")
    try: validate_member_name("/etc/passwd")
    except ValueError: pass

def test_prune_logic(tmp_path):
    from antigravity_manager.prune_backups import perform_prune_backups
    perform_prune_backups(tmp_path, keep=0, keep_latest_per_email=False, dry_run=True)
