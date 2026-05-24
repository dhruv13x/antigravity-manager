
import pytest
from antigravity_manager.ui import *
from antigravity_manager.backup import *
from antigravity_manager.restore import *
from antigravity_manager.cli import *
import argparse

def test_status_to_dict_branches():
    from antigravity_manager.status import LiveStatus, ModelQuotaStatus
    import datetime
    m = ModelQuotaStatus("a", 50, "now", datetime.datetime.now(), True)
    s = LiveStatus("t", "p", False, datetime.datetime.now(), (m,))
    assert "models" in status_to_dict(s)

def test_prune_backups_complex2(tmp_path):
    from antigravity_manager.prune_backups import perform_prune_backups
    perform_prune_backups(tmp_path, keep=0, keep_latest_per_email=False, dry_run=False)

def test_evaluate_metadata_branches():
    from antigravity_manager.cooldown import evaluate_metadata, CooldownStatus
    m = evaluate_metadata({"status": {"models": [{"is_available": True}]}}, source="backup")
    assert isinstance(m, CooldownStatus)

def test_cli_handles(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "argv", ["agm", "status"])
    monkeypatch.setattr("antigravity_manager.cli.handle_status", lambda a: None)
    try: main()
    except SystemExit: pass
