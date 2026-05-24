import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from antigravity_manager.prune_backups import perform_prune_backups

def test_perform_prune_backups_no_args():
    with patch("antigravity_manager.prune_backups.console.print") as mock_print:
        perform_prune_backups(Path("/mock"))
        mock_print.assert_called_with("Nothing to do: must specify --keep or --keep-latest-per-email")

def test_perform_prune_backups_keep_latest_per_email():
    with patch("antigravity_manager.prune_backups.iter_backup_archives") as mock_iter, \
         patch("antigravity_manager.prune_backups.build_backup_entry") as mock_build, \
         patch("antigravity_manager.prune_backups.console.print") as mock_print:

        mock_iter.return_value = [Path("/mock/b1.tar.gz"), Path("/mock/b2.tar.gz")]

        e1 = MagicMock(email="test@test.com", created_at="2023-01-02")
        e1.archive_path.name = "b1.tar.gz"
        e1.archive_path.with_name.return_value.exists.return_value = False

        e2 = MagicMock(email="test@test.com", created_at="2023-01-01")
        e2.archive_path.name = "b2.tar.gz"
        e2.archive_path.with_name.return_value.exists.return_value = False

        mock_build.side_effect = [e1, e2]

        perform_prune_backups(Path("/mock"), keep_latest_per_email=True, dry_run=True)

        mock_print.assert_called_with("Would delete b2.tar.gz")

def test_perform_prune_backups_keep_0():
    with patch("antigravity_manager.prune_backups.console.print") as mock_print:
        perform_prune_backups(Path("/mock"), keep=0)
        assert "Error" in mock_print.call_args[0][0]

def test_perform_prune_backups_keep_1():
    with patch("antigravity_manager.prune_backups.iter_backup_archives") as mock_iter, \
         patch("antigravity_manager.prune_backups.build_backup_entry") as mock_build, \
         patch("antigravity_manager.prune_backups.console.print") as mock_print:

        mock_iter.return_value = [Path("/mock/b1.tar.gz"), Path("/mock/b2.tar.gz")]

        e1 = MagicMock(email="test@test.com", created_at="2023-01-02")
        e1.archive_path.name = "b1.tar.gz"
        e1.archive_path.with_name.return_value.exists.return_value = False

        e2 = MagicMock(email="test@test.com", created_at="2023-01-01")
        e2.archive_path.name = "b2.tar.gz"
        e2.archive_path.with_name.return_value.exists.return_value = False

        mock_build.side_effect = [e1, e2]

        perform_prune_backups(Path("/mock"), keep=1, dry_run=True)

        mock_print.assert_called_with("Would delete b2.tar.gz")

def test_perform_prune_backups_execute():
    with patch("antigravity_manager.prune_backups.iter_backup_archives") as mock_iter, \
         patch("antigravity_manager.prune_backups.build_backup_entry") as mock_build, \
         patch("antigravity_manager.prune_backups.console.print") as mock_print:

        mock_iter.return_value = [Path("/mock/b1.tar.gz"), Path("/mock/b2.tar.gz")]

        e1 = MagicMock(email="test@test.com", created_at="2023-01-02")

        e2 = MagicMock(email="test@test.com", created_at="2023-01-01")
        e2.archive_path.name = "b2.tar.gz"
        meta_path = MagicMock()
        meta_path.exists.return_value = True
        meta_path.name = "b2.metadata.json"
        e2.archive_path.with_name.return_value = meta_path

        mock_build.side_effect = [e1, e2]

        perform_prune_backups(Path("/mock"), keep=1, dry_run=False)

        e2.archive_path.unlink.assert_called_once()
        meta_path.unlink.assert_called_once()

def test_perform_prune_backups_oserror():
    with patch("antigravity_manager.prune_backups.iter_backup_archives") as mock_iter, \
         patch("antigravity_manager.prune_backups.build_backup_entry") as mock_build, \
         patch("antigravity_manager.prune_backups.console.print") as mock_print:

        mock_iter.return_value = [Path("/mock/b1.tar.gz"), Path("/mock/b2.tar.gz")]

        e1 = MagicMock(email="test@test.com", created_at="2023-01-02")
        e2 = MagicMock(email="test@test.com", created_at="2023-01-01")
        e2.archive_path.unlink.side_effect = OSError("mock error")

        mock_build.side_effect = [e1, e2]

        perform_prune_backups(Path("/mock"), keep=1, dry_run=False)

        assert "Error deleting file" in mock_print.call_args[0][0]

def test_perform_prune_backups_no_match():
    with patch("antigravity_manager.prune_backups.iter_backup_archives") as mock_iter, \
         patch("antigravity_manager.prune_backups.build_backup_entry") as mock_build, \
         patch("antigravity_manager.prune_backups.console.print") as mock_print:

        mock_iter.return_value = [Path("/mock/b1.tar.gz")]

        e1 = MagicMock(email="test@test.com", created_at="2023-01-02")
        mock_build.side_effect = [e1]

        perform_prune_backups(Path("/mock"), keep=1)

        mock_print.assert_called_with("No backups matched pruning criteria.")

def test_perform_prune_backups_dry_run_with_meta():
    with patch("antigravity_manager.prune_backups.iter_backup_archives") as mock_iter, \
         patch("antigravity_manager.prune_backups.build_backup_entry") as mock_build, \
         patch("antigravity_manager.prune_backups.console.print") as mock_print:

        mock_iter.return_value = [Path("/mock/b1.tar.gz"), Path("/mock/b2.tar.gz")]

        e1 = MagicMock(email="test@test.com", created_at="2023-01-02")

        e2 = MagicMock(email="test@test.com", created_at="2023-01-01")
        e2.archive_path.name = "b2.tar.gz"
        meta_path = MagicMock()
        meta_path.exists.return_value = True
        meta_path.name = "b2.metadata.json"
        e2.archive_path.with_name.return_value = meta_path

        mock_build.side_effect = [e1, e2]

        perform_prune_backups(Path("/mock"), keep=1, dry_run=True)

        mock_print.assert_any_call("Would delete b2.tar.gz")
        mock_print.assert_any_call("Would delete b2.metadata.json")
