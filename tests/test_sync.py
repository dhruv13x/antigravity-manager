from pathlib import Path

from antigravity_manager.sync import pull_backup, push_backup


class DummyFileVersion:
    def __init__(self, name, size):
        self.file_name = name
        self.size = size


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

    def ls(self, recursive=True):
        return [(DummyFileVersion(k, v), None) for k, v in self.objects.items()]

    def upload_local_file(self, local_file, file_name):
        self.uploaded.append((local_file, file_name))

    def download_file_by_name(self, file_name):
        self.downloaded.append(file_name)
        return DummyDownloadDest(file_name)


def test_push_backup(tmp_path, monkeypatch):
    bdir = tmp_path / "backups"
    bdir.mkdir()
    f = bdir / "test.tar.gz"
    f.write_bytes(b"123")

    bucket = DummyB2Bucket({"other.tar.gz": 100})
    monkeypatch.setattr("antigravity_manager.sync._get_b2_bucket", lambda *args, **kw: bucket)

    push_backup(bdir, "mybucket", access_key="id", secret_key="key")

    assert len(bucket.uploaded) == 1
    assert bucket.uploaded[0][1] == "test.tar.gz"


def test_pull_backup(tmp_path, monkeypatch):
    bdir = tmp_path / "backups"
    bdir.mkdir()
    f = bdir / "test.tar.gz"
    f.write_bytes(b"123")

    bucket = DummyB2Bucket({"test.tar.gz": 3, "new.tar.gz": 100})
    monkeypatch.setattr("antigravity_manager.sync._get_b2_bucket", lambda *args, **kw: bucket)

    pull_backup(bdir, "mybucket", access_key="id", secret_key="key")

    assert len(bucket.downloaded) == 1
    assert bucket.downloaded[0] == "new.tar.gz"
    assert (bdir / "new.tar.gz").exists()
