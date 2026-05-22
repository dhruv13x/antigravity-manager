from __future__ import annotations

import sys
from unittest.mock import patch

import pytest
from antigravity_manager.cli import main


def test_cli_default_command_is_cooldown() -> None:
    # We mock sys.argv to simulate calling 'agm' with no arguments
    # and we mock handle_cooldown to verify it gets called with the right defaults.
    with patch("sys.argv", ["agm"]):
        with patch("antigravity_manager.cli.handle_cooldown") as mock_handle:
            main()
            mock_handle.assert_called_once()
            args = mock_handle.call_args[0][0]
            assert args.command == "cooldown"
            assert not args.json
            assert args.limit is not None


def test_cli_explicit_command_works() -> None:
    with patch("sys.argv", ["agm", "list-backups"]):
        with patch("antigravity_manager.cli.handle_list_backups") as mock_handle:
            main()
            mock_handle.assert_called_once()
            args = mock_handle.call_args[0][0]
            assert args.command == "list-backups"


def test_cli_shortcut_s_is_status() -> None:
    with patch("sys.argv", ["agm", "-s"]):
        with patch("antigravity_manager.cli.handle_status") as mock_handle:
            main()
            mock_handle.assert_called_once()
            args = mock_handle.call_args[0][0]
            assert args.command == "status"
            assert args.input_file is None


def test_cli_shortcut_c_is_cooldown() -> None:
    with patch("sys.argv", ["agm", "-c"]):
        with patch("antigravity_manager.cli.handle_cooldown") as mock_handle:
            main()
            mock_handle.assert_called_once()
            args = mock_handle.call_args[0][0]
            assert args.command == "cooldown"
            assert args.limit is not None


def test_cli_version_shortcut() -> None:
    with patch("sys.argv", ["agm", "-v"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 0
