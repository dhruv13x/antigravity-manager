from __future__ import annotations

import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.theme import Theme
from rich.prompt import Confirm
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

# Define a professional, semantic color theme
custom_theme = Theme({
    "info": "cyan",
    "warning": "bold yellow",
    "error": "bold red",
    "success": "bold green",
    "muted": "dim white",
    "accent": "bold magenta",
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
    "print_warning",
    "print_error",
    "print_info",
    "print_panel",
    "create_table",
    "create_spinner",
    "create_progress_bar"
]

def print_success(message: str) -> None:
    console.print(f"[success]✓[/success] {message}")

def print_warning(message: str) -> None:
    console.print(f"[warning]⚠[/warning] {message}")

def print_error(message: str) -> None:
    error_console.print(f"[error]✗[/error] {message}")

def print_info(message: str) -> None:
    console.print(f"[info]i[/info] {message}")

def print_panel(content: str | Table, title: str | None = None, style: str = "info") -> None:
    console.print(Panel(content, title=f"[{style}]{title}[/]" if title else None, border_style=style, expand=False, box=box.ROUNDED))

def create_table(*columns: str, title: str | None = None) -> Table:
    table = Table(show_header=True, header_style="accent", box=box.ROUNDED, title=title)
    for col in columns:
        table.add_column(col)
    return table

def create_spinner() -> Progress:
    return Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    )

def create_progress_bar() -> Progress:
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        expand=True
    )

def banner() -> None:
    from .banner import print_logo
    print_logo()

def print_rich_help() -> None:
    console.print(
        "[bold white]Usage:[/] [accent]agm[/] [muted][OPTIONS][/] [info]COMMAND[/] [muted][ARGS]...[/]\n"
    )

    # Commands Table
    cmd_table = Table(show_header=False, box=None, padding=(0, 2))
    cmd_table.add_column("Command", style="info", width=20)
    cmd_table.add_column("Description", style="white")

    commands = [
        ("interactive", "Launch the interactive CLI menu."),
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

    print_panel(cmd_table, title="Available Commands", style="accent")

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

    print_panel(opt_table, title="Options", style="warning")
    sys.exit(0)
