from __future__ import annotations

import sys
from typing import Any

from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import Button, Footer, Header, Static

from .ui import banner

class MenuApp(App[None]):
    """A Textual app to manage Antigravity Manager interactively."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        layout: grid;
        grid-size: 2;
        grid-gutter: 1 2;
        padding: 1 2;
        align: center middle;
    }

    Button {
        width: 100%;
        margin: 1 0;
    }

    .title {
        content-align: center middle;
        padding: 1;
        background: $boost;
        color: $text;
        text-style: bold;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "run_command('doctor')", "Doctor"),
        ("c", "run_command('cooldown')", "Cooldown"),
        ("s", "run_command('status')", "Status"),
        ("b", "run_command('backup')", "Backup"),
        ("r", "run_command('restore')", "Restore"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Static("Antigravity Manager Interactive Menu", classes="title")
        yield ScrollableContainer(
            Container(
                Button("🩺 Doctor", id="btn-doctor", variant="primary"),
                Button("⏱️  Cooldown", id="btn-cooldown", variant="primary"),
                Button("📊 Status", id="btn-status", variant="success"),
                Button("💾 Backup", id="btn-backup", variant="warning"),
                Button("♻️  Restore", id="btn-restore", variant="error"),
                Button("❌ Quit", id="btn-quit", variant="default"),
                id="main-container"
            )
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        button_id = event.button.id
        if button_id == "btn-quit":
            self.exit()
        elif button_id == "btn-doctor":
            self.action_run_command("doctor")
        elif button_id == "btn-cooldown":
            self.action_run_command("cooldown")
        elif button_id == "btn-status":
            self.action_run_command("status")
        elif button_id == "btn-backup":
            self.action_run_command("backup")
        elif button_id == "btn-restore":
            self.action_run_command("restore")

    def action_run_command(self, command: str) -> None:
        """Suspend Textual, run the command, then resume."""
        with self.suspend():
            print(f"\nRunning agm {command}...\n")
            try:
                # Call main directly to reuse the environment and entry point behavior
                import sys
                from antigravity_manager.cli import main
                original_argv = sys.argv[:]
                sys.argv = ["agm", command]
                main()
                sys.argv = original_argv
            except Exception as e:
                import traceback
                print(f"Error running {command}: {e}")
                traceback.print_exc()
            except SystemExit:
                pass
            finally:
                input("\nPress Enter to return to the menu...")

def run_menu() -> None:
    app = MenuApp()
    app.run()
