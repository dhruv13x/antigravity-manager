from __future__ import annotations

import argparse
import json
import tarfile
from datetime import datetime
from pathlib import Path

from antigravity_manager.backup import perform_backup, resolve_backup_anchor
from antigravity_manager.restore import perform_restore
from antigravity_manager.status import LiveStatus, ModelQuotaStatus


def make_args(**kwargs):
    return argparse.Namespace(**kwargs)


def test_auth_only_backup_and_restore_roundtrip(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "antigravity-cli"
    gemini = tmp_path / "gemini"
    backup_dir = tmp_path / "backups"
    dest = tmp_path / "dest-antigravity"
    dest_gemini = tmp_path / "dest-gemini"
    source.mkdir()
    gemini.mkdir()
    dest.mkdir()
    dest_gemini.mkdir()
    safety_dir = tmp_path / "safety"
    monkeypatch.setattr("antigravity_manager.restore.SAFETY_BACKUP_DIR", safety_dir)

    (source / "antigravity-oauth-token").write_text("new-token", encoding="utf-8")
    (source / "settings.json").write_text("{}", encoding="utf-8")
    (source / "history.jsonl").write_text("not-auth", encoding="utf-8")
    (gemini / "google_accounts.json").write_text(
        json.dumps({"active": "person@example.com"}),
        encoding="utf-8",
    )
    (dest / "antigravity-oauth-token").write_text("old-token", encoding="utf-8")
    (dest_gemini / "google_accounts.json").write_text(
        json.dumps({"active": "person@example.com"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "antigravity_manager.backup.update_registry_from_status",
        lambda status: None,
    )

    archive_path, metadata_path, metadata = perform_backup(
        make_args(
            source_dir=str(source),
            gemini_home=str(gemini),
            backup_dir=str(backup_dir),
            status_file=None,
            without_status_check=True,
            auth_only=True,
            include_bin=False,
            include_logs=False,
            decision_model="Gemini 3.5 Flash",
            dry_run=False,
            force=False,
            tmux_session_name=None,
            agy_command="agy",
            tmux_cols=140,
            tmux_rows=45,
            startup_timeout_seconds=30.0,
            usage_timeout_seconds=30.0,
        )
    )

    assert archive_path.exists()
    assert metadata_path.exists()
    assert metadata["email"] == "person@example.com"

    with tarfile.open(archive_path, "r:gz") as tar:
        names = set(tar.getnames())
    assert "antigravity-cli/antigravity-oauth-token" in names
    assert "antigravity-cli/history.jsonl" not in names
    assert "gemini/google_accounts.json" in names

    perform_restore(
        make_args(
            from_archive=str(archive_path),
            email=None,
            backup_dir=str(backup_dir),
            dest_dir=str(dest),
            gemini_home=str(dest_gemini),
            full=False,
            force=False,
            dry_run=False,
        )
    )

    assert (dest / "antigravity-oauth-token").read_text(encoding="utf-8") == "new-token"
    assert json.loads((dest_gemini / "google_accounts.json").read_text(encoding="utf-8"))["active"] == "person@example.com"
    assert any(
        path.name.endswith("-person@example.com-pre-restore-antigravity")
        for path in safety_dir.glob("*person@example.com-pre-restore-antigravity")
    )


def test_backup_anchor_prefers_gemini_flash_reset() -> None:
    captured_at = datetime.fromisoformat("2026-05-22T21:00:00+05:30")
    flash_reset = datetime.fromisoformat("2026-05-23T08:20:00+05:30")
    claude_reset = datetime.fromisoformat("2026-05-22T23:10:00+05:30")
    status = LiveStatus(
        email="person@example.com",
        plan="Google AI Pro",
        is_pro=True,
        captured_at=captured_at,
        models=(
            ModelQuotaStatus(
                model_name="Gemini 3.5 Flash (High)",
                quota_percent_left=0,
                refresh_in_text="Refreshes in 11h 20m",
                refresh_at=flash_reset,
                is_available=False,
            ),
            ModelQuotaStatus(
                model_name="Claude Sonnet 4.6 (Thinking)",
                quota_percent_left=0,
                refresh_in_text="Refreshes in 2h 10m",
                refresh_at=claude_reset,
                is_available=False,
            ),
        ),
    )

    anchor_at, source, model_name = resolve_backup_anchor(status)

    assert anchor_at == flash_reset
    assert source == "decision_model_refresh_at"
    assert model_name == "Gemini 3.5 Flash (High)"
