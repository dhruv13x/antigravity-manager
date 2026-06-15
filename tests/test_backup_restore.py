from __future__ import annotations

import argparse
import json
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Any

from antigravity_manager.backup import perform_backup, resolve_backup_anchor
from antigravity_manager.restore import (
    perform_restore,
    resolve_archive_path,
    restore_full,
    safe_extract,
    snapshot_current_state,
)
from antigravity_manager.status import LiveStatus, ModelQuotaStatus


def make_args(**kwargs: Any) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


def test_auth_only_backup_and_restore_roundtrip(tmp_path: Path, monkeypatch: Any) -> None:
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
    monkeypatch.setattr("antigravity_manager.config.ACTIVE_ACCOUNT_PATH", tmp_path / "active.json")
    monkeypatch.setattr("antigravity_manager.restore.SAFETY_BACKUP_DIR", safety_dir)

    (source / "antigravity-oauth-token").write_text("new-token", encoding="utf-8")
    (source / "cache").mkdir(parents=True, exist_ok=True)
    (source / "cache" / "onboarding.json").write_text('{"done": true}', encoding="utf-8")
    (source / "settings.json").write_text("{}", encoding="utf-8")
    (source / "history.jsonl").write_text("not-auth", encoding="utf-8")
    (source / "google_accounts.json").write_text(
        json.dumps({"active": "person@example.com"}),
        encoding="utf-8",
    )
    (gemini / "google_accounts.json").write_text(
        json.dumps({"active": "root@example.com"}),
        encoding="utf-8",
    )
    (dest / "antigravity-oauth-token").write_text("old-token", encoding="utf-8")
    (dest / "google_accounts.json").write_text(
        json.dumps({"active": "person@example.com"}),
        encoding="utf-8",
    )
    (dest_gemini / "google_accounts.json").write_text(
        json.dumps({"active": "dest-root@example.com"}),
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
            no_status=True,
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
    assert "antigravity-cli/cache/onboarding.json" in names
    assert "antigravity-cli/history.jsonl" not in names
    assert "gemini/google_accounts.json" not in names

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
    assert (dest / "cache" / "onboarding.json").read_text(encoding="utf-8") == '{"done": true}'
    assert (
        json.loads((dest_gemini / "google_accounts.json").read_text(encoding="utf-8"))["active"]
        == "dest-root@example.com"
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


def test_backup_no_decision_model_found(tmp_path: Path, monkeypatch: Any) -> None:
    source = tmp_path / "antigravity-cli"
    gemini = tmp_path / "gemini"
    backup_dir = tmp_path / "backups"
    source.mkdir()
    gemini.mkdir()
    (source / "antigravity-oauth-token").write_text("dummy-token", encoding="utf-8")
    (source / "settings.json").write_text("{}", encoding="utf-8")
    (gemini / "google_accounts.json").write_text(json.dumps({"active": "person@example.com"}))

    monkeypatch.setattr(
        "antigravity_manager.backup.update_registry_from_status", lambda status: None
    )

    # Mock capture_tmux_status_text to return a valid status text
    status_text = (
        "Account Status\ntest@example.com (Free)\nModels (1)\nOther Model\nRefreshes in 1h"
    )
    monkeypatch.setattr(
        "antigravity_manager.backup.capture_tmux_status_text", lambda **k: status_text
    )

    archive_path, metadata_path, metadata = perform_backup(
        make_args(
            source_dir=str(source),
            gemini_home=str(gemini),
            backup_dir=str(backup_dir),
            status_file=None,
            no_status=False,
            auth_only=True,
            include_bin=False,
            include_logs=False,
            decision_model="Gemini",
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
    assert metadata["backup_anchor_model"] is None


def test_backup_aborts_when_no_token(tmp_path: Path, monkeypatch: Any) -> None:
    import pytest

    source = tmp_path / "antigravity-cli"
    gemini = tmp_path / "gemini"
    backup_dir = tmp_path / "backups"
    source.mkdir()
    gemini.mkdir()
    (source / "settings.json").write_text("{}", encoding="utf-8")
    (gemini / "google_accounts.json").write_text(json.dumps({"active": "person@example.com"}))

    with pytest.raises(FileNotFoundError, match="Backup aborted because 'antigravity-oauth-token' does not exist"):
        perform_backup(
            make_args(
                source_dir=str(source),
                gemini_home=str(gemini),
                backup_dir=str(backup_dir),
                status_file=None,
                no_status=True,
                auth_only=True,
                include_bin=False,
                include_logs=False,
                decision_model="Gemini",
                dry_run=False,
                force=False,
            )
        )


def test_safe_extract_skips_absolute_symlink(tmp_path: Path) -> None:
    archive_path = tmp_path / "backup.tar.gz"
    dest_dir = tmp_path / "extract"
    dest_dir.mkdir()

    with tarfile.open(archive_path, "w:gz") as tar:
        file_data = b"{}"
        file_info = tarfile.TarInfo("antigravity-cli/settings.json")
        file_info.size = len(file_data)
        import io

        tar.addfile(file_info, io.BytesIO(file_data))
        legacy_gemini_info = tarfile.TarInfo("gemini/google_accounts.json")
        legacy_gemini_info.size = len(file_data)
        tar.addfile(legacy_gemini_info, io.BytesIO(file_data))

        link_info = tarfile.TarInfo(
            "antigravity-cli/.antigravitycli/dbe4d293-62ea-4947-9dc6-0565c9e2f462.json"
        )
        link_info.type = tarfile.SYMTYPE
        link_info.linkname = "/root/.antigravitycli/dbe4d293-62ea-4947-9dc6-0565c9e2f462.json"
        tar.addfile(link_info)

    safe_extract(archive_path, dest_dir)

    assert (dest_dir / "antigravity-cli" / "settings.json").read_text() == "{}"
    assert not (dest_dir / "gemini").exists()
    assert not (
        dest_dir
        / "antigravity-cli"
        / ".antigravitycli"
        / "dbe4d293-62ea-4947-9dc6-0565c9e2f462.json"
    ).exists()


def test_resolve_archive_path_accepts_positional_email_target(
    tmp_path: Path, monkeypatch: Any
) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    archive = backup_dir / "2026-05-25-203839-user@example.com-antigravity.tar.gz"
    archive.touch()
    archive.with_name(archive.name.replace(".tar.gz", ".metadata.json")).write_text(
        json.dumps(
            {
                "product": "antigravity",
                "email": "user@example.com",
                "plan": "Pro",
                "created_at": "2026-05-25T20:38:39+05:30",
                "captured_at": "2026-05-25T20:38:39+05:30",
                "next_available_at": "2026-05-25T20:38:39+05:30",
                "backup_mode": "auth-only",
            }
        ),
        encoding="utf-8",
    )

    resolved = resolve_archive_path(
        make_args(
            target="user@example.com",
            from_archive=None,
            email=None,
            backup_dir=str(backup_dir),
        )
    )

    assert resolved == archive.resolve()


def test_resolve_archive_path_accepts_positional_archive_filename(tmp_path: Path) -> None:
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    archive = backup_dir / "2026-05-25-203839-user@example.com-antigravity.tar.gz"
    archive.touch()

    resolved = resolve_archive_path(
        make_args(
            target=archive.name,
            from_archive=None,
            email=None,
            backup_dir=str(backup_dir),
        )
    )

    assert resolved == archive.resolve()


def test_snapshot_current_state_uses_manager_active_email(tmp_path: Path, monkeypatch: Any) -> None:
    antigravity_home = tmp_path / "antigravity-cli"
    antigravity_home.mkdir()
    safety_dir = tmp_path / "safety"
    active_path = tmp_path / "active.json"
    active_path.write_text(json.dumps({"email": "active@example.com"}), encoding="utf-8")
    monkeypatch.setattr("antigravity_manager.restore.SAFETY_BACKUP_DIR", safety_dir)
    monkeypatch.setattr("antigravity_manager.config.ACTIVE_ACCOUNT_PATH", active_path)

    snapshot = snapshot_current_state(antigravity_home=antigravity_home, dry_run=False)

    assert snapshot is not None
    assert "active@example.com-pre-restore-antigravity.tar.gz" in snapshot.name


def test_restore_full_does_not_create_safety_backup(tmp_path: Path, monkeypatch: Any) -> None:
    extracted_dir = tmp_path / "extract"
    src = extracted_dir / "antigravity-cli"
    antigravity_home = tmp_path / "dest"
    safety_dir = tmp_path / "safety"
    src.mkdir(parents=True)
    antigravity_home.mkdir()
    (src / "settings.json").write_text("{}", encoding="utf-8")
    (antigravity_home / "settings.json").write_text("old", encoding="utf-8")
    monkeypatch.setattr("antigravity_manager.restore.SAFETY_BACKUP_DIR", safety_dir)

    restore_full(
        extracted_dir,
        antigravity_home,
        dry_run=False,
        force=False,
    )

    assert not safety_dir.exists()
    assert (antigravity_home / "settings.json").read_text(encoding="utf-8") == "{}"


def test_perform_full_restore_creates_one_safety_archive(
    tmp_path: Path, monkeypatch: Any
) -> None:
    backup_dir = tmp_path / "backups"
    dest = tmp_path / "dest"
    safety_dir = tmp_path / "safety"
    backup_dir.mkdir()
    dest.mkdir()
    (dest / "google_accounts.json").write_text(
        json.dumps({"active": "current@example.com"}), encoding="utf-8"
    )
    monkeypatch.setattr("antigravity_manager.config.ACTIVE_ACCOUNT_PATH", tmp_path / "active_none.json")

    archive_path = backup_dir / "2026-05-26-145104-next@example.com-antigravity.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        settings = tmp_path / "settings.json"
        settings.write_text("{}", encoding="utf-8")
        tar.add(settings, arcname="antigravity-cli/settings.json")
    archive_path.with_name(archive_path.name.replace(".tar.gz", ".metadata.json")).write_text(
        json.dumps(
            {
                "product": "antigravity",
                "email": "next@example.com",
                "plan": "Standard",
                "created_at": "2026-05-26T14:51:04+05:30",
                "captured_at": "2026-05-26T14:51:04+05:30",
                "next_available_at": "2026-05-26T14:51:04+05:30",
                "backup_mode": "full",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("antigravity_manager.restore.SAFETY_BACKUP_DIR", safety_dir)

    _, _, _, safety_path = perform_restore(
        make_args(
            target=archive_path.name,
            from_archive=None,
            email=None,
            backup_dir=str(backup_dir),
            dest_dir=str(dest),
            full=True,
            force=False,
            dry_run=False,
        )
    )

    assert safety_path is None


def test_backup_filters_sqlite_wal_files(tmp_path: Path, monkeypatch: Any) -> None:
    source = tmp_path / "antigravity-cli"
    backup_dir = tmp_path / "backups"
    source.mkdir()
    (source / "antigravity-oauth-token").write_text("token", encoding="utf-8")
    (source / "active.db").write_text("db-content", encoding="utf-8")
    (source / "active.db-wal").write_text("wal-content", encoding="utf-8")
    (source / "active.db-shm").write_text("shm-content", encoding="utf-8")
    (source / "google_accounts.json").write_text(
        json.dumps({"active": "person@example.com"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "antigravity_manager.backup.update_registry_from_status",
        lambda status: None,
    )
    
    archive_path, _, _ = perform_backup(
        make_args(
            source_dir=str(source),
            backup_dir=str(backup_dir),
            status_file=None,
            no_status=True,
            auth_only=False,
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
    
    with tarfile.open(archive_path, "r:gz") as tar:
        names = set(tar.getnames())
    
    assert "antigravity-cli/antigravity-oauth-token" in names
    assert "antigravity-cli/active.db" in names
    assert "antigravity-cli/active.db-wal" not in names
    assert "antigravity-cli/active.db-shm" not in names
