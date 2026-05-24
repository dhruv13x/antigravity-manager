from antigravity_manager.prune import perform_prune, prune_result_to_text


class DummyArgs:
    def __init__(self, sd, dr):
        self.source_dir = sd
        self.dry_run = dr


def test_prune(tmp_path):
    (tmp_path / "log").mkdir()
    (tmp_path / "log" / "1.log").touch()

    args = DummyArgs(str(tmp_path), False)
    plan = perform_prune(args)
    assert len(plan.directories) == 1

    out = prune_result_to_text(plan, dry_run=False)
    assert "log" in out


def test_prune_preserves_credentials_and_targets_new_dirs(tmp_path):
    # Setup session-only files/dirs
    (tmp_path / "brain").mkdir()
    (tmp_path / "conversations").mkdir()
    (tmp_path / "implicit").mkdir()
    (tmp_path / "cache").mkdir()
    (tmp_path / "cache" / "last_conversations.json").touch()
    (tmp_path / "cache" / "onboarding.json").touch()
    (tmp_path / "cli.log").touch()
    (tmp_path / "last_check.timestamp").touch()
    (tmp_path / "history.jsonl").touch()

    # Setup persistent/credential files
    token_file = tmp_path / "antigravity-oauth-token"
    token_file.touch()
    settings_file = tmp_path / "settings.json"
    settings_file.touch()
    id_file = tmp_path / "installation_id"
    id_file.touch()

    args = DummyArgs(str(tmp_path), False)
    perform_prune(args)

    # Check targets were pruned
    assert not (tmp_path / "brain").exists()
    assert not (tmp_path / "conversations").exists()
    assert not (tmp_path / "implicit").exists()
    assert not (tmp_path / "cache" / "last_conversations.json").exists()
    assert not (tmp_path / "cli.log").exists()
    assert not (tmp_path / "last_check.timestamp").exists()
    assert not (tmp_path / "history.jsonl").exists()

    # Check persistent files were preserved
    assert token_file.exists()
    assert settings_file.exists()
    assert id_file.exists()
    assert (tmp_path / "cache" / "onboarding.json").exists()

    second_plan = perform_prune(args)
    assert tmp_path / "cache" not in second_plan.directories
    assert (tmp_path / "cache" / "onboarding.json").exists()
