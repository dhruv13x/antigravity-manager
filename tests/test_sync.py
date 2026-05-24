import pytest
from pathlib import Path
from antigravity_manager.sync import push_backup, pull_backup

class DummyS3Client:
    def __init__(self, objects):
        self.objects = objects
        self.uploaded = []
        self.downloaded = []

    def list_objects_v2(self, Bucket):
        if not self.objects:
            return {}
        return {"Contents": [{"Key": k, "Size": v} for k, v in self.objects.items()]}

    def upload_file(self, file_path, bucket, key):
        self.uploaded.append((file_path, key))

    def download_file(self, bucket, key, file_path):
        self.downloaded.append((key, file_path))
        Path(file_path).write_bytes(b"dummy")

def test_push_backup(tmp_path, monkeypatch):
    bdir = tmp_path / "backups"
    bdir.mkdir()
    f = bdir / "test.tar.gz"
    f.write_bytes(b"123")

    client = DummyS3Client({"other.tar.gz": 100})
    monkeypatch.setattr("antigravity_manager.sync._get_s3_client", lambda *args, **kw: client)

    push_backup(bdir, "mybucket")

    assert len(client.uploaded) == 1
    assert client.uploaded[0][1] == "test.tar.gz"

def test_pull_backup(tmp_path, monkeypatch):
    bdir = tmp_path / "backups"
    bdir.mkdir()
    f = bdir / "test.tar.gz"
    f.write_bytes(b"123")

    client = DummyS3Client({"test.tar.gz": 3, "new.tar.gz": 100})
    monkeypatch.setattr("antigravity_manager.sync._get_s3_client", lambda *args, **kw: client)

    pull_backup(bdir, "mybucket")

    assert len(client.downloaded) == 1
    assert client.downloaded[0][0] == "new.tar.gz"
    assert (bdir / "new.tar.gz").exists()
