from antigravity_manager.registry import save_registry
from antigravity_manager.remove import perform_remove, remove_result_to_text


class DummyArgs:
    def __init__(self, email, backup_dir, yes=False, dry_run=False, cloud=False):
        self.email = email
        self.backup_dir = backup_dir
        self.yes = yes
        self.dry_run = dry_run
        self.cloud = cloud


def test_perform_remove_local(tmp_path, monkeypatch):
    bdir = tmp_path / "backups"
    bdir.mkdir()
    (bdir / "2026-05-24-123456-user@example.com-antigravity.tar.gz").touch()
    (bdir / "user@example.com-latest-antigravity.tar.gz").touch()
    (bdir / "2026-05-24-123456-other@example.com-antigravity.tar.gz").touch()

    registry = {"user@example.com": {"reset_at": "xxx"}, "other@example.com": {"reset_at": "yyy"}}

    rpath = tmp_path / "r.json"
    rpath.write_text("{}")
    monkeypatch.setattr("antigravity_manager.registry.COOLDOWN_REGISTRY_PATH", rpath)
    save_registry(registry)

    args = DummyArgs("user@example.com", str(bdir), yes=True)
    results = perform_remove(args)

    assert len(results["local_files_removed"]) == 2
    assert any(
        "2026-05-24-123456-user@example.com-antigravity.tar.gz" in f
        for f in results["local_files_removed"]
    )
    assert any(
        "user@example.com-latest-antigravity.tar.gz" in f for f in results["local_files_removed"]
    )
    assert results["local_registry_removed"] is True

    assert not (bdir / "2026-05-24-123456-user@example.com-antigravity.tar.gz").exists()
    assert not (bdir / "user@example.com-latest-antigravity.tar.gz").exists()
    assert (bdir / "2026-05-24-123456-other@example.com-antigravity.tar.gz").exists()


def test_remove_result_to_text():
    results = {
        "local_files_removed": ["file1.tar.gz"],
        "local_registry_removed": True,
    }
    out = remove_result_to_text(results, "user@example.com", False)
    assert out is not None
    assert out is not None
    assert out is not None
    assert out is not None
