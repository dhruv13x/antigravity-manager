from antigravity_manager.prune_backups import perform_prune_backups


def test_prune_backups(tmp_path):
    b = tmp_path / "backups"
    b.mkdir()

    # create some
    (b / "u_1.tar.gz").touch()
    (b / "u_2.tar.gz").touch()

    perform_prune_backups(b, keep=1, dry_run=False)
    # wait, prune backups is tested?


def test_prune_backups_deletes_duplicate_metadata_only_entries(tmp_path):
    b = tmp_path / "backups"
    b.mkdir()
    for stamp in ["2026-05-25T10:00:00+05:30", "2026-05-26T10:00:00+05:30"]:
        safe_stamp = stamp[:10]
        (b / f"{safe_stamp}-user@example.com-antigravity.metadata.json").write_text(
            (
                '{"product":"antigravity","email":"user@example.com",'
                f'"created_at":"{stamp}","captured_at":"{stamp}",'
                f'"archive_name":"{safe_stamp}-user@example.com-antigravity.tar.gz"}}'
            ),
            encoding="utf-8",
        )

    deleted = perform_prune_backups(b, keep=1, dry_run=False)

    assert (b / "2026-05-26-user@example.com-antigravity.metadata.json").exists()
    assert not (b / "2026-05-25-user@example.com-antigravity.metadata.json").exists()
    assert [path.name for path in deleted] == [
        "2026-05-25-user@example.com-antigravity.metadata.json"
    ]
