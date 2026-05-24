from antigravity_manager.prune_backups import perform_prune_backups


def test_prune_backups(tmp_path):
    b = tmp_path / "backups"
    b.mkdir()

    # create some
    (b / "u_1.tar.gz").touch()
    (b / "u_2.tar.gz").touch()

    perform_prune_backups(b, keep=1, dry_run=False)
    # wait, prune backups is tested?
