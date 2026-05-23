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
