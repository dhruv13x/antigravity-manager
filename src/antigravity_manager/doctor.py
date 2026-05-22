from __future__ import annotations

import shutil
from pathlib import Path


def run_doctor(*, antigravity_home: Path, gemini_home: Path, backup_dir: Path) -> list[tuple[str, bool, str]]:
    checks = [
        ("tmux", shutil.which("tmux") is not None, shutil.which("tmux") or "missing"),
        ("agy", shutil.which("agy") is not None, shutil.which("agy") or "missing"),
        ("antigravity_home", antigravity_home.is_dir(), str(antigravity_home)),
        ("gemini_home", gemini_home.is_dir(), str(gemini_home)),
        ("backup_dir", backup_dir.exists(), str(backup_dir)),
    ]
    return checks


def print_doctor_table(checks: list[tuple[str, bool, str]]) -> None:
    from .ui import Panel, Table, console

    table = Table(show_header=True, header_style="bold bright_magenta")
    table.add_column("Check", style="bright_cyan")
    table.add_column("Status", justify="center")
    table.add_column("Detail", style="dim")

    for name, ok, detail in checks:
        table.add_row(
            name,
            "[bold bright_green]OK[/]" if ok else "[bold red]MISSING[/]",
            detail,
        )
    console.print(Panel(table, title="[bold bright_cyan]Antigravity Manager Doctor[/]", border_style="bright_cyan", expand=False))
