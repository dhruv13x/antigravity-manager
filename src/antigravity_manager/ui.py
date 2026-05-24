from __future__ import annotations

import sys
from typing import Any

from rich.align import Align
from rich.console import Console
from rich.padding import Padding
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

console = Console()
error_console = Console(stderr=True)

__all__ = [
    "Align",
    "Console",
    "Padding",
    "Panel",
    "Table",
    "Text",
    "Tree",
    "console",
    "error_console",
    "Confirm",
    "banner",
    "print_rich_help",
    "format_badge",
    "print_header",
    "print_success",
    "print_error",
    "print_warning",
    "print_info",
    "render_dict_as_table",
]


def format_badge(text: str, style: str = "white on blue") -> Text:
    return Text(f" {text} ", style=style)


def print_header(title: str, subtitle: str | None = None) -> None:
    text = Text(title, style="bold bright_cyan")
    if subtitle:
        text.append(f" - {subtitle}", style="dim")
    console.print(Panel(text, border_style="bright_cyan", expand=False))


def print_success(title: str, details: list[str] | None = None) -> None:
    text = Text(title, style="bold bright_green")
    if details:
        text.append("\n")
        for detail in details:
            text.append(f"\n✓ {detail}", style="bright_green")
    console.print(
        Panel(
            text,
            border_style="bright_green",
            title="[bold green]Success[/]",
            title_align="left",
            expand=False,
        )
    )


def print_error(msg: str) -> None:
    error_console.print(
        Panel(
            f"[bold red]{msg}[/]",
            border_style="red",
            title="[bold red]Error[/]",
            title_align="left",
            expand=False,
        )
    )


def print_warning(msg: str) -> None:
    console.print(
        Panel(
            f"[bold bright_yellow]{msg}[/]",
            border_style="bright_yellow",
            title="[bold bright_yellow]Warning[/]",
            title_align="left",
            expand=False,
        )
    )


def print_info(msg: str) -> None:
    console.print(
        Panel(
            f"[bold bright_blue]{msg}[/]",
            border_style="bright_blue",
            title="[bold bright_blue]Info[/]",
            title_align="left",
            expand=False,
        )
    )


def render_dict_as_table(data: dict[str, Any], title: str | None = None) -> Table:
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan")
    table.add_column("Value", style="white")
    for k, v in data.items():
        if isinstance(v, bool):
            val_str = "[bold bright_green]True[/]" if v else "[bold bright_red]False[/]"
        elif v is None:
            val_str = "[dim]None[/]"
        else:
            val_str = str(v)
        table.add_row(str(k), val_str)

    if title:
        table.title = f"[bold magenta]{title}[/]"
        table.title_justify = "left"
    return table


def banner() -> None:
    from .banner import print_logo

    print_logo()


def print_rich_help() -> None:
    console.print(
        "[bold white]Usage:[/] [bold cyan]agm[/] [dim][OPTIONS][/] [bold magenta]COMMAND[/] [dim][ARGS]...[/]\n"
    )

    cmd_table = Table(show_header=False, box=None, padding=(0, 2))
    cmd_table.add_column("Command", style="bold cyan", width=20)
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
        Panel(cmd_table, title="[bold magenta]Available Commands[/]", border_style="cyan")
    )

    opt_table = Table(show_header=False, box=None, padding=(0, 2))
    opt_table.add_column("Option", style="bold yellow", width=20)
    opt_table.add_column("Description", style="white")

    options = [
        ("--status, -s", "Shortcut for 'status' command."),
        ("--cooldown, -c", "Shortcut for 'cooldown' command."),
        ("--version, -v", "Show program's version number and exit."),
        ("--help, -h", "Show this message and exit."),
    ]

    for opt, desc in options:
        opt_table.add_row(opt, desc)

    console.print(Panel(opt_table, title="[bold yellow]Options[/]", border_style="green"))
    sys.exit(0)
