from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .ui import Confirm, console, print_info, print_warning, print_error, print_success, print_panel, Table


def perform_purge(args: Any) -> bool:
    source_dir = Path(args.source_dir).expanduser()

    if not source_dir.exists():
        print_info(f"Antigravity directory does not exist: [dim]{source_dir}[/]")
        return False

    if not args.yes and not args.dry_run:
        print_warning(f"This will COMPLETELY DELETE [cyan]{source_dir}[/]")
        print_warning("This includes your authentication, session history, and all account identity files.")
        if not Confirm.ask("[warning]Are you sure you want to proceed with the purge?[/]"):
            print_info("Purge cancelled.")
            return False

    if args.dry_run:
        print_warning(f"\\[DRY RUN] Would completely remove [cyan]{source_dir}[/]")
        return True

    try:
        if source_dir.is_dir():
            shutil.rmtree(source_dir)
        else:
            source_dir.unlink()
        return True
    except Exception as exc:
        print_error(f"Failed to purge {source_dir}: {exc}")
        return False


def purge_result_to_text(success: bool, source_dir: Path, dry_run: bool) -> str:
    if not success and not dry_run:
        return "Purge failed or was cancelled."

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Property", style="info")
    table.add_column("Value", style="muted")

    table.add_row("Mode", "[warning]DRY RUN[/]" if dry_run else "[success]PURGED[/]")
    table.add_row("Source Dir", str(source_dir))
    table.add_row("Status", "[success]SUCCESS[/]" if success else "[warning]SKIPPED[/]")

    print_panel(table, title="Purge Result", style="success" if success else "warning")

    if success and not dry_run:
        print_success("Antigravity home has been factory reset.")
        print_info("Next time you run Antigravity, it will treat it as a first-time setup.")

    return ""
