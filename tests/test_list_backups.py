import pytest
from pathlib import Path
import json
import tarfile
from unittest.mock import patch, MagicMock

from antigravity_manager.list_backups import (
    BackupEntry,
    metadata_path_for_archive,
    load_metadata_for_archive,
    build_backup_entry,
    iter_backup_archives,
    list_backups,
    parse_dt,
    print_entries_table
)

def test_backup_entry_creation():
    entry = BackupEntry(
        archive_path=Path("/tmp/foo.tar.gz"),
        email="user@test.com",
        plan="premium",
        created_at="now",
        captured_at="now",
        next_available_at="later",
        backup_mode="full",
        metadata={"foo": "bar"}
    )
    assert entry.email == "user@test.com"
    assert entry.plan == "premium"

def test_metadata_path_for_archive():
    archive_path = Path("/tmp/my-backup-antigravity.tar.gz")
    meta_path = metadata_path_for_archive(archive_path)
    assert meta_path == Path("/tmp/my-backup-antigravity.metadata.json")

def test_load_metadata_for_archive_from_file():
    archive_path = Path("/tmp/backup.tar.gz")
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.read_text", return_value='{"key": "value"}'):
        data = load_metadata_for_archive(archive_path)
        assert data == {"key": "value"}

def test_load_metadata_for_archive_from_tarball():
    archive_path = Path("/tmp/backup.tar.gz")
    with patch("pathlib.Path.exists", return_value=False), \
         patch("tarfile.open") as mock_tar_open:

        mock_tar = MagicMock()
        mock_member = MagicMock()
        mock_tar.getmember.return_value = mock_member

        mock_file = MagicMock()
        mock_file.read.return_value = b'{"key": "value"}'
        mock_tar.extractfile.return_value = mock_file

        mock_tar_open.return_value.__enter__.return_value = mock_tar

        data = load_metadata_for_archive(archive_path)
        assert data == {"key": "value"}
        mock_tar.getmember.assert_called_once_with("backup.metadata.json")

def test_build_backup_entry_success():
    archive_path = Path("/tmp/backup.tar.gz")
    with patch("antigravity_manager.list_backups.load_metadata_for_archive") as mock_load:
        mock_load.return_value = {
            "product": "antigravity",
            "email": "test@test.com"
        }
        entry = build_backup_entry(archive_path)
        assert entry is not None
        assert entry.email == "test@test.com"

def test_build_backup_entry_wrong_product():
    archive_path = Path("/tmp/backup.tar.gz")
    with patch("antigravity_manager.list_backups.load_metadata_for_archive") as mock_load:
        mock_load.return_value = {
            "product": "other",
            "email": "test@test.com"
        }
        entry = build_backup_entry(archive_path)
        assert entry is None

def test_build_backup_entry_load_error():
    archive_path = Path("/tmp/backup.tar.gz")
    with patch("antigravity_manager.list_backups.load_metadata_for_archive", side_effect=Exception("error")):
        entry = build_backup_entry(archive_path)
        assert entry is None

def test_iter_backup_archives_not_exists():
    backup_dir = Path("/nonexistent")
    with patch("pathlib.Path.exists", return_value=False):
        assert iter_backup_archives(backup_dir) == []

def test_iter_backup_archives_success():
    backup_dir = Path("/tmp")
    with patch("pathlib.Path.exists", return_value=True), \
         patch("pathlib.Path.glob") as mock_glob:

        mock_glob.return_value = [
            Path("/tmp/a-antigravity.tar.gz"),
            Path("/tmp/b-latest-antigravity.tar.gz"), # Should be filtered out
            Path("/tmp/c-antigravity.tar.gz")
        ]

        res = iter_backup_archives(backup_dir)
        assert len(res) == 2
        # sorted by name reverse
        assert res[0].name == "c-antigravity.tar.gz"
        assert res[1].name == "a-antigravity.tar.gz"

def test_list_backups_basic():
    backup_dir = Path("/tmp")
    with patch("antigravity_manager.list_backups.iter_backup_archives") as mock_iter, \
         patch("antigravity_manager.list_backups.build_backup_entry") as mock_build:

        mock_iter.return_value = [Path("/tmp/a.tar.gz"), Path("/tmp/b.tar.gz")]

        entry1 = MagicMock(email="test1@test.com", created_at="2023-01-02")
        entry2 = MagicMock(email="test2@test.com", created_at="2023-01-01")

        mock_build.side_effect = [entry1, entry2]

        res = list_backups(backup_dir)
        assert len(res) == 2
        # sorted by created_at reverse
        assert res[0] == entry1
        assert res[1] == entry2

def test_list_backups_with_email_filter():
    backup_dir = Path("/tmp")
    with patch("antigravity_manager.list_backups.iter_backup_archives") as mock_iter, \
         patch("antigravity_manager.list_backups.build_backup_entry") as mock_build:

        mock_iter.return_value = [Path("/tmp/a.tar.gz"), Path("/tmp/b.tar.gz")]

        entry1 = MagicMock(email="test1@test.com", created_at="2023-01-02")
        entry2 = MagicMock(email="test2@test.com", created_at="2023-01-01")

        mock_build.side_effect = [entry1, entry2]

        res = list_backups(backup_dir, email="test2@test.com")
        assert len(res) == 1
        assert res[0] == entry2

def test_list_backups_latest_per_email():
    backup_dir = Path("/tmp")
    with patch("antigravity_manager.list_backups.iter_backup_archives") as mock_iter, \
         patch("antigravity_manager.list_backups.build_backup_entry") as mock_build:

        mock_iter.return_value = [Path("/tmp/a.tar.gz"), Path("/tmp/b.tar.gz"), Path("/tmp/c.tar.gz")]

        entry1 = MagicMock(email="test@test.com", created_at="2023-01-03")
        entry2 = MagicMock(email="test@test.com", created_at="2023-01-02")
        entry3 = MagicMock(email="other@test.com", created_at="2023-01-01")

        mock_build.side_effect = [entry1, entry2, entry3]

        res = list_backups(backup_dir, latest_per_email=True)
        assert len(res) == 2
        assert res[0] == entry1
        assert res[1] == entry3

def test_parse_dt():
    assert parse_dt("invalid") is None
    dt = parse_dt("2023-01-01T12:00:00")
    assert dt is not None
    assert dt.year == 2023

def test_print_entries_table():
    entry = MagicMock(
        archive_path=Path("/tmp/backup.tar.gz"),
        email="test@test.com",
        plan="premium",
        backup_mode="full",
        captured_at="now",
        next_available_at="later"
    )
    with patch("antigravity_manager.ui.console.print") as mock_print:
        print_entries_table([entry])
        mock_print.assert_called_once()
