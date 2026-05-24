from __future__ import annotations

import sys

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from rich.tree import Tree

# Centralized theme
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "danger": "bold red",
    "success": "bold green",
    "accent": "bold cyan",
    "muted": "dim white",
    "highlight": "bold bright_magenta"
})

console = Console(theme=custom_theme)
error_console = Console(stderr=True, theme=custom_theme)

__all__ = [
    "Panel",
    "Table",
    "console",
    "error_console",
    "Confirm",
    "banner",
    "print_rich_help",
    "Text",
    "Tree",
    "Align",
    "Group"
]


def banner() -> None:
    from .banner import print_logo
    print_logo()


def print_rich_help() -> None:
    console.print(
        "[bold white]Usage:[/] [accent]agm[/] [muted][OPTIONS][/] [highlight]COMMAND[/] [muted][ARGS]...[/]\n"
    )

    # Commands Table
    cmd_table = Table(show_header=False, box=None, padding=(0, 2))
    cmd_table.add_column("Command", style="accent", width=20)
    cmd_table.add_column("Description", style="white")

    commands = [
        ("status", "Capture and parse live Antigravity /usage status."),
        ("backup", "Create an Antigravity backup archive."),
        ("restore", "Restore an Antigravity backup."),
        ("cooldown", "Show account/model availability from registry."),
        ("list-backups", "List available Antigravity backups."),
        ("recommend", "Recommend the best account to use next."),
        ("use", "Auth-only restore for a specific account."),
        ("doctor", "Check local Antigravity Manager prerequisites."),
        ("prune", "Prune temporary runtime state."),
        ("prune-backups", "Delete old backup archives and metadata."),
        ("purge", "Completely reset Antigravity state."),
        ("remove", "Remove all traces of a specific account."),
        ("profile", "Export or import manager profile."),
        ("sync", "Sync backups with S3 bucket."),
        ("check-cloud", "Verify cloud credentials."),
    ]

    for cmd, desc in commands:
        cmd_table.add_row(cmd, desc)

    console.print(
        Panel(cmd_table, title="[highlight]Available Commands[/]", border_style="cyan", expand=False)
    )

    # Options Table
    opt_table = Table(show_header=False, box=None, padding=(0, 2))
    opt_table.add_column("Option", style="warning", width=20)
    opt_table.add_column("Description", style="white")

    options = [
        ("--status, -s", "Shortcut for 'status' command."),
        ("--cooldown, -c", "Shortcut for 'cooldown' command."),
        ("--version, -v", "Show program's version number and exit."),
        ("--help, -h", "Show this message and exit."),
    ]

    for opt, desc in options:
        opt_table.add_row(opt, desc)

    console.print(Panel(opt_table, title="[warning]Options[/]", border_style="green", expand=False))
    sys.exit(0)
