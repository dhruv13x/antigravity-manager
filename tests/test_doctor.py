import pytest
from pathlib import Path
from unittest.mock import patch
from antigravity_manager.doctor import run_doctor, print_doctor_table

def test_run_doctor_all_ok():
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/mock"

        antigravity_home = Path("/mock/antigravity")
        gemini_home = Path("/mock/gemini")
        backup_dir = Path("/mock/backups")

        with patch.object(Path, 'is_dir', return_value=True), \
             patch.object(Path, 'exists', return_value=True):

            checks = run_doctor(
                antigravity_home=antigravity_home,
                gemini_home=gemini_home,
                backup_dir=backup_dir
            )

            assert len(checks) == 5
            for name, ok, detail in checks:
                assert ok is True

def test_run_doctor_all_missing():
    with patch("shutil.which") as mock_which:
        mock_which.return_value = None

        antigravity_home = Path("/mock/antigravity")
        gemini_home = Path("/mock/gemini")
        backup_dir = Path("/mock/backups")

        with patch.object(Path, 'is_dir', return_value=False), \
             patch.object(Path, 'exists', return_value=False):

            checks = run_doctor(
                antigravity_home=antigravity_home,
                gemini_home=gemini_home,
                backup_dir=backup_dir
            )

            assert len(checks) == 5
            for name, ok, detail in checks:
                assert ok is False

def test_print_doctor_table():
    checks = [
        ("tmux", True, "/usr/bin/tmux"),
        ("missing_tool", False, "missing")
    ]
    with patch("antigravity_manager.ui.console.print") as mock_print:
        print_doctor_table(checks)
        mock_print.assert_called_once()
