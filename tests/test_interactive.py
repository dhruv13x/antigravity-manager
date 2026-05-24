from unittest.mock import MagicMock
import pytest
from antigravity_manager.interactive import interactive_menu
from argparse import Namespace

def test_interactive_menu_exit(monkeypatch, capsys):
    mock_questionary = MagicMock()
    mock_ask = MagicMock(return_value="Exit")
    mock_select = MagicMock(return_value=MagicMock(ask=mock_ask))
    monkeypatch.setattr("questionary.select", mock_select)

    with pytest.raises(SystemExit) as exit_info:
        interactive_menu(Namespace(command="interactive"))

    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert "Exiting Antigravity Manager." in captured.out
