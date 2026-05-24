from __future__ import annotations

import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn, TransferSpeedColumn

custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "primary": "magenta",
    "secondary": "blue",
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
    "print_success",
    "print_error",
    "print_warning",
    "print_info",
    "print_panel",
    "get_progress"
]

def print_success(message: str) -> None:
    console.print(f"[success]✓[/success] {message}")

def print_error(message: str) -> None:
    error_console.print(f"[error]✗[/error] {message}")

def print_warning(message: str) -> None:
    console.print(f"[warning]![/warning] {message}")

def print_info(message: str) -> None:
    console.print(f"[info]i[/info] {message}")

def print_panel(content: str, title: str | None = None, style: str = "primary") -> None:
    console.print(Panel(content, title=title, border_style=style, expand=False))

def get_progress(transient: bool = True) -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumn(),
        transient=transient,
    )


def banner() -> None:
    from .banner import print_logo
    print_logo()


def print_rich_help() -> None:
    console.print(
        "[bold white]Usage:[/] [bold cyan]agm[/] [dim][OPTIONS][/] [bold magenta]COMMAND[/] [dim][ARGS]...[/]\n"
    )

    # Commands Table
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
        ("menu", "Launch interactive terminal menu."),
    ]

    for cmd, desc in commands:
        cmd_table.add_row(cmd, desc)

    console.print(
        Panel(cmd_table, title="[bold magenta]Available Commands[/]", border_style="cyan")
    )

    # Options Table
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


from rich.prompt import Confirm
