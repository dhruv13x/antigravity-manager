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


def _copy_snapshot_item(path: Path, snapshot_dir: Path, name: str) -> None:
    target = snapshot_dir / name
    if path.is_dir() and not path.is_symlink():
        shutil.copytree(
            path,
            target,
            symlinks=True,
            ignore=shutil.ignore_patterns("log", "updater", "knowledge"),
        )
    else:
        shutil.copy2(path, target)


def safety_snapshot(
    source_dir: Path, *, dry_run: bool, extra_paths: list[Path] | None = None
) -> Path | None:
    snapshot_paths = [
        path for path in [source_dir, *(extra_paths or [])] if path.exists() or path.is_symlink()
    ]
    if dry_run or not snapshot_paths:
        return None
    email = read_active_email(source_dir) or "unknown"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    snapshot_dir = SAFETY_BACKUP_DIR / f"{timestamp}-{safe_label(email)}-pre-purge-antigravity"
    snapshot_dir.mkdir(parents=True, exist_ok=False)
    if source_dir.exists() or source_dir.is_symlink():
        _copy_snapshot_item(source_dir, snapshot_dir, "antigravity-cli")
    for path in extra_paths or []:
        if path.exists():
            _copy_snapshot_item(path, snapshot_dir, safe_label(path.name))
    return snapshot_dir


def perform_purge(args: Any) -> bool:
    source_dir = Path(args.source_dir).expanduser()
    extra_paths = []
    if getattr(args, "gemini_config_dir", None):
        extra_paths.append(Path(args.gemini_config_dir).expanduser())
    if getattr(args, "session_dir", None):
        extra_paths.append(Path(args.session_dir).expanduser())
    targets = [source_dir]
    seen = {source_dir.resolve()}
    for path in extra_paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        targets.append(path)
        seen.add(resolved)

    if not any(path.exists() or path.is_symlink() for path in targets):
        console.print(f"[yellow]Note:[/] Antigravity state does not exist: [dim]{source_dir}[/]")
        return False

    if not args.yes and not args.dry_run:
        console.print("\n[bold red]WARNING:[/] This will COMPLETELY DELETE Antigravity state.")
        for path in targets:
            if path.exists() or path.is_symlink():
                console.print(f"Target: [cyan]{path}[/]")
        console.print(
            "[red]This includes your authentication, session history, and all account identity files.[/]"
        )
        if not Confirm.ask("[bold yellow]Are you sure you want to proceed with the purge?[/]"):
            console.print("[blue]Purge cancelled.[/]")
            return False

    if args.dry_run:
        for path in targets:
            if path.exists() or path.is_symlink():
                console.print(f"[bold yellow]Dry-run:[/] Would completely remove [cyan]{path}[/]")
        return True

    try:
        snapshot = safety_snapshot(source_dir, dry_run=False, extra_paths=extra_paths)
        for path in targets:
            if not path.exists() and not path.is_symlink():
                continue
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
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
