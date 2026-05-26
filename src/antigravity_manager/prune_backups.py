from __future__ import annotations

from pathlib import Path

from .list_backups import (
    BackupEntry,
    list_backups,
    list_status_metadata,
    metadata_path_for_archive,
)
from .ui import console


def _filter_to_delete(
    entries: list[BackupEntry], keep: int | None, keep_latest_per_email: bool
) -> list[BackupEntry]:
    to_delete = []

    if keep_latest_per_email:
        seen_emails = set()
        kept = []
        for e in entries:
            if e.email not in seen_emails:
                seen_emails.add(e.email)
                kept.append(e)
            else:
                to_delete.append(e)
        entries = kept

    if keep is not None:
        if keep < 1:
            # We don't error here as it might be part of a larger batch
            # but we follow the policy of keeping at least one.
            keep = 1

        email_counts: dict[str, int] = {}
        kept = []
        for e in entries:
            count = email_counts.get(e.email, 0)
            if count < keep:
                email_counts[e.email] = count + 1
                kept.append(e)
            else:
                to_delete.append(e)
        entries = kept

    return to_delete


def perform_prune_backups(
    backup_dir: Path,
    keep: int | None = None,
    keep_latest_per_email: bool = False,
    dry_run: bool = False,
) -> list[Path]:
    if keep is None and not keep_latest_per_email:
        console.print("Nothing to do: must specify --keep or --keep-latest-per-email")
        return []

    if keep is not None and keep < 1:
        console.print(
            "[bold red]Error:[/] --keep 0 is not executable. One copy per email backup "
            "will always stay until manually deleted by the user."
        )
        return []

    backup_entries = list_backups(backup_dir, latest_per_email=False)
    status_entries = list_status_metadata(backup_dir, latest_per_email=False)

    to_delete = _filter_to_delete(backup_entries, keep, keep_latest_per_email)
    to_delete.extend(_filter_to_delete(status_entries, keep, keep_latest_per_email))

    if not to_delete:
        console.print("No backups or status events matched pruning criteria.")
        return []

    deleted_paths: list[Path] = []

    for entry in to_delete:
        # For backups, we also need to delete the metadata file
        metadata_path = None
        if entry.source == "backup":
            metadata_path = metadata_path_for_archive(entry.archive_path)

        if dry_run:
            console.print(f"Would delete {entry.source}: {entry.archive_path.name}")
            deleted_paths.append(entry.archive_path)
            if metadata_path and metadata_path.exists():
                console.print(f"Would delete metadata: {metadata_path.name}")
                deleted_paths.append(metadata_path)
            continue

        try:
            if entry.archive_path.exists() or entry.archive_path.is_symlink():
                console.print(f"Deleting {entry.source}: {entry.archive_path.name}...")
                entry.archive_path.unlink()
                deleted_paths.append(entry.archive_path)
            if metadata_path and metadata_path.exists():
                console.print(f"Deleting metadata: {metadata_path.name}...")
                metadata_path.unlink()
                deleted_paths.append(metadata_path)
        except OSError as e:
            console.print(f"Error deleting file: {e}")

    return deleted_paths
