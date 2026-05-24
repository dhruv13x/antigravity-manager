from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from rich.console import Group
from rich.text import Text

from .ui import Confirm, Panel, console, render_dict_as_table


def perform_purge(args: Any) -> bool:
    source_dir = Path(args.source_dir).expanduser()

    if not source_dir.exists():
        console.print(
            f"[yellow]Note:[/] Antigravity directory does not exist: [dim]{source_dir}[/]"
        )
        return False

    if not args.yes and not args.dry_run:
        console.print(f"\n[bold red]WARNING:[/] This will COMPLETELY DELETE [cyan]{source_dir}[/]")
        console.print(
            "[red]This includes your authentication, session history, and all account identity files.[/]"
        )
        if not Confirm.ask("[bold yellow]Are you sure you want to proceed with the purge?[/]"):
            console.print("[blue]Purge cancelled.[/]")
            return False

    if args.dry_run:
        console.print(f"[bold yellow]Dry-run:[/] Would completely remove [cyan]{source_dir}[/]")
        return True

    try:
        if source_dir.is_dir():
            shutil.rmtree(source_dir)
        else:
            source_dir.unlink()
        return True
    except Exception as exc:
        console.print(f"[bold red]Error:[/] Failed to purge {source_dir}: {exc}")
        return False


def purge_result_to_text(success: bool, source_dir: Path, dry_run: bool) -> Panel | str:
    if not success and not dry_run:
        return Panel(
            "[bold red]Purge failed or was cancelled.[/]",
            title="[bold red]Purge[/]",
            border_style="red",
            expand=False,
        )

    title = (
        "[bold yellow]Dry Run: Purge Plan[/]" if dry_run else "[bold bright_red]Purge Completed[/]"
    )

    data = {
        "Source Dir": str(source_dir),
        "Status": "[bold bright_green]SUCCESS[/]" if success else "[bold yellow]SKIPPED[/]",
    }

    table = render_dict_as_table(data)
    renderables = [table]

    if success and not dry_run:
        text = Text("\nAntigravity home has been factory reset.\n", style="bold green")
        text.append(
            "Next time you run Antigravity, it will treat it as a first-time setup.", style="dim"
        )
        renderables.append(text)

    return Panel(
        Group(*renderables),
        title=title,
        border_style="yellow" if dry_run else "bright_red",
        expand=False,
    )
