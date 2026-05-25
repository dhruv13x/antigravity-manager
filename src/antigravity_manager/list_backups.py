from __future__ import annotations

import json
import tarfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BackupEntry:
    archive_path: Path
    email: str
    plan: str
    created_at: str
    captured_at: str
    next_available_at: str
    backup_mode: str
    metadata: dict[str, Any]
    source: str = "backup"


def metadata_path_for_archive(archive_path: Path) -> Path:
    # email-timestamp-antigravity.tar.gz -> email-timestamp-antigravity.metadata.json
    # email-timestamp-antigravity.tar.gz.gpg -> email-timestamp-antigravity.metadata.json
    name = archive_path.name.replace(".tar.gz.gpg", ".metadata.json").replace(
        ".tar.gz", ".metadata.json"
    )
    return archive_path.with_name(name)


def load_metadata_for_archive(archive_path: Path) -> dict[str, Any]:
    metadata_path = metadata_path_for_archive(archive_path)
    if metadata_path.exists():
        return dict(json.loads(metadata_path.read_text(encoding="utf-8")))

    # Fallback to internal metadata for unencrypted archives
    if archive_path.suffix != ".gpg":
        member_name = archive_path.name.replace(".tar.gz", ".metadata.json")
        with tarfile.open(archive_path, "r:gz") as tar:
            member = tar.getmember(member_name)
            extracted = tar.extractfile(member)
            if extracted is None:
                raise FileNotFoundError(f"Metadata member could not be read: {member_name}")
            return dict(json.loads(extracted.read().decode("utf-8")))

    raise FileNotFoundError(f"External metadata missing for encrypted archive: {archive_path}")


def build_backup_entry(archive_path: Path) -> BackupEntry | None:
    try:
        metadata = load_metadata_for_archive(archive_path)
    except Exception:
        return None
    if metadata.get("product") != "antigravity":
        return None
    return BackupEntry(
        archive_path=archive_path,
        email=metadata.get("email", "unknown"),
        plan=metadata.get("plan", "unknown"),
        created_at=metadata.get("created_at", "unknown"),
        captured_at=metadata.get("captured_at", "unknown"),
        next_available_at=metadata.get("next_available_at", "unknown"),
        backup_mode=metadata.get("backup_mode", "unknown"),
        metadata=metadata,
    )


def iter_backup_archives(backup_dir: Path) -> list[Path]:
    if not backup_dir.exists():
        return []
    archives = list(backup_dir.glob("*-antigravity.tar.gz")) + list(
        backup_dir.glob("*-antigravity.tar.gz.gpg")
    )
    return sorted(
        [path for path in archives if "-latest-antigravity.tar.gz" not in path.name],
        key=lambda path: path.name,
        reverse=True,
    )


def iter_status_metadata_files(backup_dir: Path) -> list[Path]:
    if not backup_dir.exists():
        return []
    return sorted(
        backup_dir.glob("*.status.metadata.json"), key=lambda path: path.name, reverse=True
    )


def build_status_metadata_entry(metadata_path: Path) -> BackupEntry | None:
    try:
        metadata = dict(json.loads(metadata_path.read_text(encoding="utf-8")))
    except Exception:
        return None
    if metadata.get("product") != "antigravity":
        return None
    if metadata.get("record_type") != "status":
        return None
    return BackupEntry(
        archive_path=metadata_path,
        email=metadata.get("email", "unknown"),
        plan=metadata.get("plan", "unknown"),
        created_at=metadata.get("created_at", "unknown"),
        captured_at=metadata.get("captured_at", "unknown"),
        next_available_at=metadata.get("next_available_at", "unknown"),
        backup_mode=metadata.get("backup_mode", "status-only"),
        metadata=metadata,
        source="status",
    )


def list_status_metadata(
    backup_dir: Path,
    *,
    email: str | None = None,
    latest_per_email: bool = False,
) -> list[BackupEntry]:
    entries = [
        entry
        for entry in (
            build_status_metadata_entry(path) for path in iter_status_metadata_files(backup_dir)
        )
        if entry is not None
    ]
    if email:
        entries = [entry for entry in entries if entry.email == email]

    entries.sort(key=lambda entry: entry.captured_at or entry.created_at, reverse=True)
    if latest_per_email:
        seen: set[str] = set()
        latest = []
        for entry in entries:
            if entry.email in seen:
                continue
            seen.add(entry.email)
            latest.append(entry)
        entries = latest
    return entries


def list_backups(
    backup_dir: Path,
    *,
    email: str | None = None,
    latest_per_email: bool = False,
) -> list[BackupEntry]:
    entries = [
        entry
        for entry in (build_backup_entry(path) for path in iter_backup_archives(backup_dir))
        if entry is not None
    ]
    if email:
        entries = [entry for entry in entries if entry.email == email]

    entries.sort(key=lambda entry: entry.created_at, reverse=True)
    if latest_per_email:
        seen: set[str] = set()
        latest = []
        for entry in entries:
            if entry.email in seen:
                continue
            seen.add(entry.email)
            latest.append(entry)
        entries = latest
    return entries


def parse_dt(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def print_entries_table(entries: list[BackupEntry]) -> None:
    from .ui import Panel, Table, console

    table = Table(show_header=True, header_style="bold bright_magenta")
    table.add_column("Archive", style="bright_cyan")
    table.add_column("Email", style="bright_green")
    table.add_column("Plan")
    table.add_column("Mode", justify="center")
    table.add_column("Captured", justify="right", style="dim")
    table.add_column("Next Available", justify="right", style="bright_yellow")

    for entry in entries:
        if entry.email == "unknown":
            continue
        table.add_row(
            entry.archive_path.name,
            entry.email,
            entry.plan,
            entry.backup_mode,
            entry.captured_at,
            entry.next_available_at,
        )
    console.print(
        Panel(
            table,
            title="[bold bright_cyan]Antigravity Backups[/]",
            border_style="bright_cyan",
            expand=False,
        )
    )
