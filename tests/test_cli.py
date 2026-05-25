from __future__ import annotations

import argparse
from typing import Any

from antigravity_manager.cli import build_parser


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


def test_cli_use_accepts_target() -> None:
    parser = build_parser()
    args = parser.parse_args(["use", "person@example.com"])
    assert args.command == "use"
    assert args.target == "person@example.com"


def test_cli_restore_accepts_target_and_auth_only_flag() -> None:
    parser = build_parser()
    args = parser.parse_args(["restore", "backup.tar.gz", "--auth-only"])
    assert args.command == "restore"
    assert args.target == "backup.tar.gz"
    assert args.auth_only is True
    assert args.full is None


def test_cli_recommend_restore_flag() -> None:
    parser = build_parser()
    args = parser.parse_args(["recommend", "--restore"])
    assert args.command == "recommend"
    assert args.restore is True


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
