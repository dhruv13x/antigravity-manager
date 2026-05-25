from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import SAFETY_BACKUP_DIR
from .ui import Confirm, console
from .utils import safe_label


def read_active_email(source_dir: Path) -> str | None:
    try:
        data = json.loads((source_dir / "google_accounts.json").read_text(encoding="utf-8"))
    except Exception:
        return None
    active = data.get("active")
    return active.strip() if isinstance(active, str) and active.strip() else None


def safety_snapshot(source_dir: Path, *, dry_run: bool) -> Path | None:
    if dry_run or not source_dir.exists():
        return None
    email = read_active_email(source_dir) or "unknown"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    snapshot_dir = SAFETY_BACKUP_DIR / f"{timestamp}-{safe_label(email)}-pre-purge-antigravity"
    snapshot_dir.mkdir(parents=True, exist_ok=False)
    if source_dir.is_dir():
        shutil.copytree(
            source_dir,
            snapshot_dir / "antigravity-cli",
            symlinks=True,
            ignore=shutil.ignore_patterns("log", "updater", "knowledge"),
        )
    else:
        shutil.copy2(source_dir, snapshot_dir / source_dir.name)
    return snapshot_dir


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
        snapshot = safety_snapshot(source_dir, dry_run=False)
        if source_dir.is_dir():
            shutil.rmtree(source_dir)
        else:
            source_dir.unlink()
        if snapshot:
            console.print(f"[green]Safety backup:[/] {snapshot}")
        return True
    except Exception as exc:
        console.print(f"[bold red]Error:[/] Failed to purge {source_dir}: {exc}")
        return False


def purge_result_to_text(success: bool, source_dir: Path, dry_run: bool) -> str:
    if not success and not dry_run:
        return "Purge failed or was cancelled."

    lines = [
        f"mode: {'dry-run' if dry_run else 'purged'}",
        f"source_dir: {source_dir}",
        f"status: {'SUCCESS' if success else 'SKIPPED'}",
    ]
    if success and not dry_run:
        lines.append("\n[bold green]Antigravity home has been factory reset.[/]")
        lines.append("Next time you run Antigravity, it will treat it as a first-time setup.")

    return "\n".join(lines)
