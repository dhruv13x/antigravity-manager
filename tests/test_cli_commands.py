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

    # Create a fake AGM_HOME
    fake_agm_home = tmp_path / "agm-home"
    fake_agm_home.mkdir()

    # Monkeypatch AGM_HOME in both config and profile modules
    monkeypatch.setattr("antigravity_manager.config.AGM_HOME", fake_agm_home)
    monkeypatch.setattr("antigravity_manager.profile.AGM_HOME", fake_agm_home)

    monkeypatch.setattr(
        sys, "argv", ["agm", "profile", "export", str(tmp_path / "p.tar.gz"), "--dry-run"]
    )
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

    source_dir = tmp_path / "antigravity"
    config_dir = tmp_path / "config"
    session_dir = tmp_path / "sessions"
    source_dir.mkdir()
    config_dir.mkdir()
    session_dir.mkdir()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "agm",
            "purge",
            "-y",
            "--source-dir",
            str(source_dir),
            "--gemini-config-dir",
            str(config_dir),
            "--session-dir",
            str(session_dir),
        ],
    )
    monkeypatch.setattr("antigravity_manager.purge.shutil.rmtree", lambda *a, **kw: None)
    monkeypatch.setattr("antigravity_manager.purge.Confirm.ask", lambda *a, **kw: True)
    main()


def test_cli_remove_yes(monkeypatch, tmp_path, capsys):
    import sys

    monkeypatch.setattr(sys, "argv", ["agm", "remove", "user@example.com", "-y"])
    main()


def test_cli_profile_import(monkeypatch, tmp_path, capsys):
    import sys

    # Create a fake AGM_HOME
    fake_agm_home = tmp_path / "agm-home"
    fake_agm_home.mkdir()

    # Monkeypatch AGM_HOME in both config and profile modules
    monkeypatch.setattr("antigravity_manager.config.AGM_HOME", fake_agm_home)
    monkeypatch.setattr("antigravity_manager.profile.AGM_HOME", fake_agm_home)

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


def test_cli_sync_auto(monkeypatch, tmp_path, capsys):
    import sys

    monkeypatch.setattr(sys, "argv", ["agm", "sync", "auto", "--bucket-name", "b", "--dry-run"])
    import antigravity_manager.cli

    monkeypatch.setattr(
        "antigravity_manager.cli.resolve_credentials",
        lambda *a, **kw: ("key", "secret", "b", "url"),
    )
    pulled = False
    pushed = False
    def fake_pull(*a, **kw):
        nonlocal pulled
        pulled = True
        print("pulled!")
    def fake_push(*a, **kw):
        nonlocal pushed
        pushed = True
        print("pushed!")

    monkeypatch.setattr("antigravity_manager.sync._get_b2_bucket", lambda *a, **kw: "dummy_bucket")
    monkeypatch.setattr("antigravity_manager.sync.deduplicate_cloud", lambda *a, **kw: None)
    monkeypatch.setattr("antigravity_manager.sync.pull_backup", fake_pull)
    monkeypatch.setattr("antigravity_manager.sync.push_backup", fake_push)

    main()
    captured = capsys.readouterr()
    assert "pulled!" in captured.out
    assert "pushed!" in captured.out
    assert pulled is True
    assert pushed is True
