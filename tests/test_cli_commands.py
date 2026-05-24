from antigravity_manager.cli import main


def test_cli_purge(monkeypatch, tmp_path, capsys):
    import sys

    monkeypatch.setattr(sys, "argv", ["agm", "purge", "--dry-run"])
    main()
    captured = capsys.readouterr()
    assert "dry-run" in captured.out.lower() or "dry run" in captured.out.lower()


def test_cli_remove(monkeypatch, tmp_path, capsys):
    import sys

    monkeypatch.setattr(sys, "argv", ["agm", "remove", "user@example.com", "--dry-run"])
    main()
    captured = capsys.readouterr()
    assert "dry-run" in captured.out.lower() or "dry run" in captured.out.lower()


def test_cli_profile(monkeypatch, tmp_path, capsys):
    import sys

    monkeypatch.setattr(sys, "argv", ["agm", "profile", "export", "/tmp/p.tar.gz", "--dry-run"])
    main()
    captured = capsys.readouterr()
    assert "Would export profile" in captured.out


def test_cli_sync(monkeypatch, tmp_path, capsys):
    import sys

    monkeypatch.setattr(sys, "argv", ["agm", "sync", "push", "--bucket-name", "b", "--dry-run"])

    # We mock push_backup directly
    import antigravity_manager.cli

    monkeypatch.setattr(
        "antigravity_manager.cli.resolve_credentials",
        lambda *a, **kw: ("key", "secret", "b", "url"),
    )
    monkeypatch.setattr(antigravity_manager.cli, "push_backup", lambda *a, **kw: print("pushed!"))

    main()
    captured = capsys.readouterr()
    assert "pushed!" in captured.out


def test_cli_purge_yes(monkeypatch, tmp_path, capsys):
    import sys

    monkeypatch.setattr(sys, "argv", ["agm", "purge", "--yes"])
    monkeypatch.setattr("antigravity_manager.purge.shutil.rmtree", lambda *a, **kw: None)
    monkeypatch.setattr("antigravity_manager.purge.Confirm.ask", lambda *a, **kw: True)
    main()


def test_cli_remove_yes(monkeypatch, tmp_path, capsys):
    import sys

    monkeypatch.setattr(sys, "argv", ["agm", "remove", "user@example.com", "--yes"])
    main()


def test_cli_profile_import(monkeypatch, tmp_path, capsys):
    import sys

    (tmp_path / "p.tar.gz").touch()
    monkeypatch.setattr(
        sys, "argv", ["agm", "profile", "import", str(tmp_path / "p.tar.gz"), "--dry-run"]
    )
    main()
    captured = capsys.readouterr()
    assert "Would import profile" in captured.out


def test_cli_sync_pull(monkeypatch, tmp_path, capsys):
    import sys

    monkeypatch.setattr(sys, "argv", ["agm", "sync", "pull", "--bucket-name", "b", "--dry-run"])
    import antigravity_manager.cli

    monkeypatch.setattr(
        "antigravity_manager.cli.resolve_credentials",
        lambda *a, **kw: ("key", "secret", "b", "url"),
    )
    monkeypatch.setattr(antigravity_manager.cli, "pull_backup", lambda *a, **kw: print("pulled!"))
    main()
    captured = capsys.readouterr()
    assert "pulled!" in captured.out
