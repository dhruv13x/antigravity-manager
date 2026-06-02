import pytest
from pathlib import Path
from antigravity_manager.sync import push_backup, pull_backup, pull_cloud_index

class DummyFileVersion:
    def __init__(self, name, size):
        self.file_name = name
        self.size = size
        self.id_ = f"id-{name}"

class DummyDownloadDest:
    def __init__(self, key):
        self.key = key
    def save_to(self, path):
        Path(path).write_bytes(b"dummy")

class DummyB2Bucket:
    def __init__(self, objects):
        self.objects = objects
        self.uploaded = []
        self.downloaded = []
        self.deleted = []

    def ls(self, recursive=True):
        return [(DummyFileVersion(k, v), None) for k, v in self.objects.items()]

    def upload_local_file(self, local_file, file_name):
        self.uploaded.append((local_file, file_name))

    def download_file_by_name(self, file_name):
        self.downloaded.append(file_name)
        return DummyDownloadDest(file_name)

    def delete_file_version(self, file_id, file_name):
        self.deleted.append((file_id, file_name))

def test_push_backup(tmp_path, monkeypatch):
    bdir = tmp_path / "backups"
    bdir.mkdir()
    f = bdir / "test.tar.gz"
    f.write_bytes(b"123")
    meta_file = bdir / "user@example.com-latest-antigravity.metadata.json"
    meta_file.write_bytes(b"{}")

    bucket = DummyB2Bucket({"other.tar.gz": 100})
    monkeypatch.setattr("antigravity_manager.sync._get_b2_bucket", lambda *args, **kw: bucket)

    push_backup(bdir, "mybucket", access_key="id", secret_key="key")

    assert len(bucket.uploaded) == 2
    assert {item[1] for item in bucket.uploaded} == {
        "test.tar.gz",
        "user@example.com-latest-antigravity.metadata.json",
    }

def test_pull_backup(tmp_path, monkeypatch):
    bdir = tmp_path / "backups"
    bdir.mkdir()
    f = bdir / "test.tar.gz"
    f.write_bytes(b"123")

    bucket = DummyB2Bucket({"test.tar.gz": 3, "user@example.com-latest-antigravity.metadata.json": 100})
    monkeypatch.setattr("antigravity_manager.sync._get_b2_bucket", lambda *args, **kw: bucket)

    pull_backup(bdir, "mybucket", access_key="id", secret_key="key")

    assert len(bucket.downloaded) == 1
    assert bucket.downloaded[0] == "user@example.com-latest-antigravity.metadata.json"
    assert (bdir / "user@example.com-latest-antigravity.metadata.json").exists()


def test_pull_cloud_index_skips_archives(tmp_path, monkeypatch):
    bdir = tmp_path / "backups"
    bdir.mkdir()

    bucket = DummyB2Bucket(
        {
            "backup.tar.gz": 100,
            "backup.metadata.json": 10,
        }
    )
    monkeypatch.setattr("antigravity_manager.sync._get_b2_bucket", lambda *args, **kw: bucket)

    pull_cloud_index(bdir, "mybucket", access_key="id", secret_key="key")

    assert bucket.downloaded == ["backup.metadata.json"]
    assert not (bdir / "backup.tar.gz").exists()
    assert (bdir / "backup.metadata.json").exists()


def test_delete_cloud_account_objects(monkeypatch):
    from antigravity_manager.sync import delete_cloud_account_objects

    bucket = DummyB2Bucket(
        {
            "2026-user@example.com-antigravity.tar.gz": 10,
            "2026-user@example.com-antigravity.metadata.json": 10,
            "status/events/status__email_user@example.com.json": 10,
            "other@example.com-latest-antigravity.tar.gz": 10,
        }
    )
    monkeypatch.setattr("antigravity_manager.sync._get_b2_bucket", lambda *args, **kw: bucket)

    removed = delete_cloud_account_objects(
        email="user@example.com",
        bucket_name="mybucket",
        access_key="id",
        secret_key="key",
    )

    assert removed == [
        "2026-user@example.com-antigravity.tar.gz",
        "2026-user@example.com-antigravity.metadata.json",
        "status/events/status__email_user@example.com.json",
    ]
    assert [item[1] for item in bucket.deleted] == removed


def test_delete_cloud_objects(monkeypatch):
    from antigravity_manager.sync import delete_cloud_objects

    bucket = DummyB2Bucket(
        {
            "a.tar.gz": 10,
            "a.metadata.json": 10,
            "b.tar.gz": 10,
        }
    )
    monkeypatch.setattr("antigravity_manager.sync._get_b2_bucket", lambda *args, **kw: bucket)

    removed = delete_cloud_objects(
        object_names=["a.tar.gz", "a.metadata.json"],
        bucket_name="mybucket",
        access_key="id",
        secret_key="key",
    )

    assert removed == ["a.tar.gz", "a.metadata.json"]
    assert [item[1] for item in bucket.deleted] == removed
