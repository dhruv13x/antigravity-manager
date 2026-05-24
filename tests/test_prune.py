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
