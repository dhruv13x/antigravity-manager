from __future__ import annotations

import argparse
from datetime import datetime
from typing import Any

from antigravity_manager.cli import (
    build_parser,
    handle_status,
    handle_use,
    save_status_metadata,
    status_metadata_timestamp,
)
from antigravity_manager.status import AntigravityStatusError, LiveStatus, ModelQuotaStatus


def make_args(**kwargs: Any) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


def test_cli_default_command_is_cooldown(monkeypatch: Any) -> None:
    parser = build_parser()
    args = parser.parse_args([])
    assert args.command is None
    assert getattr(args, "cooldown", False) is False


def test_cli_explicit_command_works() -> None:
    parser = build_parser()
    args = parser.parse_args(["status", "--json"])
    assert args.command == "status"
    assert args.json is True
    assert args.no_save is False


def test_cli_list_backups_defaults_to_latest_per_account() -> None:
    parser = build_parser()
    args = parser.parse_args(["list-backups"])
    assert args.command == "list-backups"
    assert args.all is False

    args = parser.parse_args(["list-backups", "--all"])
    assert args.command == "list-backups"
    assert args.all is True

    args = parser.parse_args(["list-backups", "--cloud", "--bucket-name", "b"])
    assert args.cloud is True
    assert args.bucket_name == "b"


def test_cli_use_accepts_target() -> None:
    parser = build_parser()
    args = parser.parse_args(["use", "person@example.com"])
    assert args.command == "use"
    assert args.target == "person@example.com"
    assert args.no_status_check is False

    args = parser.parse_args(["use", "person@example.com", "--no-status"])
    assert args.no_status_check is True

    args = parser.parse_args(["use", "person@example.com", "--cloud", "--bucket-name", "b"])
    assert args.cloud is True


def test_cli_restore_accepts_target_and_auth_only_flag() -> None:
    parser = build_parser()
    args = parser.parse_args(["restore", "backup.tar.gz", "--auth-only"])
    assert args.command == "restore"
    assert args.target == "backup.tar.gz"
    assert args.auth_only is True
    assert args.full is None
    assert args.no_status_check is False

    args = parser.parse_args(["restore", "backup.tar.gz", "--cloud", "--bucket-name", "b"])
    assert args.cloud is True


def test_cli_recommend_restore_flag() -> None:
    parser = build_parser()
    args = parser.parse_args(["recommend", "--restore", "--no-status-check"])
    assert args.command == "recommend"
    assert args.restore is True
    assert args.no_status_check is True

    args = parser.parse_args(["recommend", "--cloud", "--bucket-name", "b"])
    assert args.cloud is True


def test_cli_short_yes_aliases() -> None:
    parser = build_parser()
    args = parser.parse_args(["purge", "-y"])
    assert args.command == "purge"
    assert args.yes is True

    args = parser.parse_args(["remove", "person@example.com", "-y"])
    assert args.command == "remove"
    assert args.yes is True


def test_cli_check_cloud_removed() -> None:
    import pytest

    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["check-cloud"])


def test_cli_shortcut_s_is_status() -> None:
    parser = build_parser()
    args = parser.parse_args(["-s"])
    assert args.status is True


def test_cli_shortcut_c_is_cooldown() -> None:
    parser = build_parser()
    args = parser.parse_args(["-c"])
    assert getattr(args, "cooldown", False) is True


def test_cli_version_shortcut() -> None:
    import pytest

    parser = build_parser()
    with pytest.raises(SystemExit) as excinfo:
        parser.parse_args(["-v"])
    assert excinfo.value.code == 0


def test_handle_use_aborts_when_status_capture_fails(monkeypatch: Any, tmp_path: Any) -> None:
    import pytest

    dest_dir = tmp_path / "dest"
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / "antigravity-oauth-token").touch()

    args = make_args(
        target="person@example.com",
        backup_dir=str(tmp_path),
        dest_dir=str(dest_dir),
        dry_run=False,
        no_status_check=False,
        tmux_session_name=None,
        agy_command="agy",
        tmux_cols=140,
        tmux_rows=45,
        startup_timeout_seconds=30.0,
        usage_timeout_seconds=30.0,
    )
    monkeypatch.setattr(
        "antigravity_manager.cli.capture_tmux_status_text",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("broken")),
    )
    called = False

    def fake_restore(_: Any) -> tuple[Path, dict, list, None]:
        nonlocal called
        called = True
        return (tmp_path / "a.tar.gz", {"email": "person@example.com"}, [], None)

    monkeypatch.setattr("antigravity_manager.cli.perform_restore", fake_restore)

    with pytest.raises(AntigravityStatusError):
        handle_use(args)
    assert called is False


def test_handle_use_bypasses_status_check_if_no_token(monkeypatch: Any, tmp_path: Any) -> None:
    dest_dir = tmp_path / "dest"
    dest_dir.mkdir(parents=True, exist_ok=True)

    args = make_args(
        target="person@example.com",
        backup_dir=str(tmp_path),
        dest_dir=str(dest_dir),
        dry_run=False,
        no_status_check=False,
        tmux_session_name=None,
        agy_command="agy",
        tmux_cols=140,
        tmux_rows=45,
        startup_timeout_seconds=30.0,
        usage_timeout_seconds=30.0,
    )

    status_check_called = False
    def fake_capture(**kwargs):
        nonlocal status_check_called
        status_check_called = True
        return "person@example.com (Standard)\nModel Quota\n"

    monkeypatch.setattr(
        "antigravity_manager.cli.capture_tmux_status_text",
        fake_capture,
    )

    called = False
    def fake_restore(_: Any) -> tuple[Path, dict, list, None]:
        nonlocal called
        called = True
        return (tmp_path / "a.tar.gz", {"email": "person@example.com"}, [], None)

    monkeypatch.setattr("antigravity_manager.cli.perform_restore", fake_restore)
    monkeypatch.setattr("antigravity_manager.cli.save_active_account", lambda *a, **kw: None)

    handle_use(args)
    assert status_check_called is False
    assert called is True


def test_handle_use_no_status_check_skips_capture(monkeypatch: Any, tmp_path: Any) -> None:
    args = make_args(
        target="person@example.com",
        backup_dir=str(tmp_path),
        dest_dir=str(tmp_path / "dest"),
        dry_run=False,
        no_status_check=True,
    )
    monkeypatch.setattr(
        "antigravity_manager.cli.capture_tmux_status_text",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("should not run")),
    )
    monkeypatch.setattr(
        "antigravity_manager.cli.perform_restore",
        lambda _: (tmp_path / "a.tar.gz", {"email": "person@example.com"}, [], None),
    )
    monkeypatch.setattr("antigravity_manager.cli.save_active_account", lambda *a, **kw: None)
    handle_use(args)


def test_status_metadata_timestamp_prefers_gemini_flash_high() -> None:
    captured_at = datetime.fromisoformat("2026-05-26T10:00:00+05:30")
    refresh_at = datetime.fromisoformat("2026-05-26T15:00:00+05:30")
    status = LiveStatus(
        email="person@example.com",
        plan="Standard",
        is_pro=False,
        captured_at=captured_at,
        models=(
            ModelQuotaStatus(
                model_name="Gemini 3.5 Flash (High)",
                quota_percent_left=0,
                refresh_in_text="Refreshes in 5h",
                refresh_at=refresh_at,
                is_available=False,
            ),
        ),
    )
    assert status_metadata_timestamp(status) == refresh_at


def test_save_status_metadata_writes_cloud_listable_event_and_latest(tmp_path: Any) -> None:
    captured_at = datetime.fromisoformat("2026-05-26T10:00:00+05:30")
    refresh_at = datetime.fromisoformat("2026-05-26T15:00:00+05:30")
    status = LiveStatus(
        email="person@example.com",
        plan="Standard",
        is_pro=False,
        captured_at=captured_at,
        models=(
            ModelQuotaStatus(
                model_name="Gemini 3.5 Flash (High)",
                quota_percent_left=0,
                refresh_in_text="Refreshes in 5h",
                refresh_at=refresh_at,
                is_available=False,
            ),
        ),
    )

    latest_path = save_status_metadata(status, tmp_path)
    expected_path = tmp_path / "status" / "latest" / "person@example.com.status.json"

    assert latest_path == expected_path
    assert latest_path.exists()


def test_handle_status_marks_active_account(monkeypatch: Any, tmp_path: Any) -> None:
    called: dict[str, str] = {}
    monkeypatch.setattr(
        "antigravity_manager.cli.capture_tmux_status_text",
        lambda **kwargs: "person@example.com (Standard)\nModel Quota\n",
    )
    monkeypatch.setattr("antigravity_manager.cli.update_registry_from_status", lambda status: None)
    monkeypatch.setattr(
        "antigravity_manager.cli.save_status_metadata",
        lambda status, backup_dir: tmp_path / "status.metadata.json",
    )
    monkeypatch.setattr(
        "antigravity_manager.cli.save_active_account",
        lambda email: called.setdefault("email", email),
    )
    handle_status(
        make_args(
            input_file=None,
            backup_dir=str(tmp_path),
            no_save=False,
            json=True,
            tmux_session_name=None,
            agy_command="agy",
            tmux_cols=140,
            tmux_rows=45,
            startup_timeout_seconds=30.0,
            usage_timeout_seconds=30.0,
        )
    )
    assert called["email"] == "person@example.com"
