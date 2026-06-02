from __future__ import annotations

from pathlib import Path
from typing import Any

from b2sdk.v2 import B2Api, InMemoryAccountInfo
from rich.console import Console

from .ui import console

console_stderr = Console(stderr=True)


def _get_b2_bucket(key_id: str, app_key: str, bucket_name: str) -> Any:
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", key_id, app_key)
    return b2_api.get_bucket_by_name(bucket_name)


def push_backup(
    backup_dir: Path,
    bucket_name: str,
    endpoint_url: str | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
    dry_run: bool = False,
) -> None:
    if not access_key or not secret_key:
        console_stderr.print("[bold red]Missing B2 credentials (KEY_ID or APP_KEY).[/]")
        return

    try:
        bucket = _get_b2_bucket(access_key, secret_key, bucket_name)
    except Exception as e:
        console_stderr.print(f"[bold red]Failed to connect to B2 bucket {bucket_name}: {e}[/]")
        return

    # Fetch remote state
    remote_files = {}
    try:
        for file_version, _ in bucket.ls(recursive=True):
            remote_files[file_version.file_name] = file_version.size
    except Exception as e:
        console_stderr.print(f"[bold red]Failed to list remote bucket {bucket_name}: {e}[/]")
        return

    # Push backup archives/metadata and nested status index files.
    backup_files = sorted(
        list(backup_dir.glob("*.tar.gz"))
        + list(backup_dir.glob("*.tar.gz.gpg"))
        + list(backup_dir.glob("*.metadata.json"))
        + list(backup_dir.glob("status/**/*.json"))
    )

    for file_path in backup_files:
        if not file_path.is_file() or file_path.is_symlink():
            continue

        object_name = str(file_path.relative_to(backup_dir))

        # Check if file exists and has the same size
        if object_name in remote_files and remote_files[object_name] == file_path.stat().st_size:
            console.print(f"Skipping {file_path.name}, already exists in cloud with same size.")
            continue

        if dry_run:
            console.print(f"Would push {file_path.name} to b2://{bucket_name}/{object_name}")
            continue

        try:
            console.print(f"Uploading {file_path.name} to b2://{bucket_name}/{object_name}...")
            bucket.upload_local_file(local_file=str(file_path), file_name=object_name)
            console.print(f"[green]Successfully uploaded {file_path.name}[/]")
        except Exception as e:
            console_stderr.print(f"[bold red]Failed to upload {file_path.name}: {e}[/]")


def pull_backup(
    backup_dir: Path,
    bucket_name: str,
    endpoint_url: str | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
    dry_run: bool = False,
) -> None:
    if not access_key or not secret_key:
        console_stderr.print("[bold red]Missing B2 credentials (KEY_ID or APP_KEY).[/]")
        return

    try:
        bucket = _get_b2_bucket(access_key, secret_key, bucket_name)
    except Exception as e:
        console_stderr.print(f"[bold red]Failed to connect to B2 bucket {bucket_name}: {e}[/]")
        return

    backup_dir.mkdir(parents=True, exist_ok=True)

    # Use a set for O(1) lookup
    local_files = {
        str(p.relative_to(backup_dir)) for p in backup_dir.rglob("*") if p.is_file()
    }

    try:
        remote_versions = list(bucket.ls(recursive=True))
        if not remote_versions:
            console.print(f"No objects found in bucket {bucket_name}")
            return

        for file_version, _ in remote_versions:
            object_name = file_version.file_name
            file_path = backup_dir / object_name

            if object_name in local_files:
                console.print(f"Skipping {object_name}, already exists locally.")
                continue

            if dry_run:
                console.print(f"Would pull b2://{bucket_name}/{object_name} to {file_path}")
                continue

            try:
                file_path.parent.mkdir(parents=True, exist_ok=True)
                console.print(f"Downloading b2://{bucket_name}/{object_name} to {file_path}...")
                download_dest = bucket.download_file_by_name(object_name)
                download_dest.save_to(str(file_path))
                console.print(f"[green]Successfully downloaded {object_name}[/]")
            except Exception as e:
                console_stderr.print(f"[bold red]Failed to download {object_name}: {e}[/]")
    except Exception as e:
        console_stderr.print(f"[bold red]Failed to sync with bucket {bucket_name}: {e}[/]")


def pull_cloud_index(
    backup_dir: Path,
    bucket_name: str,
    endpoint_url: str | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
    dry_run: bool = False,
) -> None:
    if not access_key or not secret_key:
        console_stderr.print("[bold red]Missing B2 credentials (KEY_ID or APP_KEY).[/]")
        return

    try:
        bucket = _get_b2_bucket(access_key, secret_key, bucket_name)
    except Exception as e:
        console_stderr.print(f"[bold red]Failed to connect to B2 bucket {bucket_name}: {e}[/]")
        return

    backup_dir.mkdir(parents=True, exist_ok=True)
    local_files = {
        str(p.relative_to(backup_dir)) for p in backup_dir.rglob("*") if p.is_file()
    }
    try:
        for file_version, _ in bucket.ls(recursive=True):
            object_name = file_version.file_name
            is_index = object_name.endswith(".metadata.json") or object_name.startswith("status/")
            if not is_index or object_name in local_files:
                continue
            file_path = backup_dir / object_name
            if dry_run:
                console.print(f"Would pull b2://{bucket_name}/{object_name} to {file_path}")
                continue
            file_path.parent.mkdir(parents=True, exist_ok=True)
            download_dest = bucket.download_file_by_name(object_name)
            download_dest.save_to(str(file_path))
    except Exception as e:
        console_stderr.print(f"[bold red]Failed to pull cloud index from {bucket_name}: {e}[/]")


def delete_cloud_account_objects(
    *,
    email: str,
    bucket_name: str,
    endpoint_url: str | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
    dry_run: bool = False,
) -> list[str]:
    if not access_key or not secret_key:
        console_stderr.print("[bold red]Missing B2 credentials (KEY_ID or APP_KEY).[/]")
        return []
    try:
        bucket = _get_b2_bucket(access_key, secret_key, bucket_name)
    except Exception as e:
        console_stderr.print(f"[bold red]Failed to connect to B2 bucket {bucket_name}: {e}[/]")
        return []

    removed: list[str] = []
    for file_version, _ in bucket.ls(recursive=True):
        object_name = file_version.file_name
        is_match = (
            f"-{email}-" in object_name
            or object_name.startswith(f"{email}-latest-")
            or f"email_{email}" in object_name
            or object_name.endswith(f"/{email}.status.json")
        )
        if not is_match:
            continue
        removed.append(object_name)
        if dry_run:
            console.print(f"Would delete b2://{bucket_name}/{object_name}")
            continue
        file_id = getattr(file_version, "id_", None) or getattr(file_version, "file_id", None)
        if file_id:
            bucket.delete_file_version(file_id, object_name)
        elif hasattr(bucket, "hide_file"):
            bucket.hide_file(object_name)
        else:
            console_stderr.print(f"[yellow]Could not delete {object_name}: missing file id[/]")
    return removed


def delete_cloud_objects(
    *,
    object_names: list[str],
    bucket_name: str,
    endpoint_url: str | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
    dry_run: bool = False,
) -> list[str]:
    if not object_names:
        return []
    if not access_key or not secret_key:
        console_stderr.print("[bold red]Missing B2 credentials (KEY_ID or APP_KEY).[/]")
        return []
    try:
        bucket = _get_b2_bucket(access_key, secret_key, bucket_name)
    except Exception as e:
        console_stderr.print(f"[bold red]Failed to connect to B2 bucket {bucket_name}: {e}[/]")
        return []

    wanted = set(object_names)
    removed: list[str] = []
    for file_version, _ in bucket.ls(recursive=True):
        object_name = file_version.file_name
        if object_name not in wanted:
            continue
        removed.append(object_name)
        if dry_run:
            console.print(f"Would delete b2://{bucket_name}/{object_name}")
            continue
        file_id = getattr(file_version, "id_", None) or getattr(file_version, "file_id", None)
        if file_id:
            bucket.delete_file_version(file_id, object_name)
        elif hasattr(bucket, "hide_file"):
            bucket.hide_file(object_name)
        else:
            console_stderr.print(f"[yellow]Could not delete {object_name}: missing file id[/]")
    return removed


def verify_cloud_connectivity(
    bucket_name: str,
    endpoint_url: str | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
) -> bool:
    """Verifies that the cloud bucket is accessible with the provided credentials."""
    if not access_key or not secret_key:
        return False
    try:
        bucket = _get_b2_bucket(access_key, secret_key, bucket_name)
        # Try to list to verify access
        for _ in bucket.ls(recursive=True):
            break
        return True
    except Exception as e:
        console_stderr.print(f"[bold red]Cloud verification failed for {bucket_name}: {e}[/]")
        return False


def deduplicate_and_upgrade_local(backup_dir: Path, dry_run: bool = False) -> None:
    if not backup_dir.exists():
        return

    import json
    import shutil
    from .list_backups import list_backups, metadata_path_for_archive
    from .utils import safe_label

    entries = list_backups(backup_dir, latest_per_email=False)
    by_email: dict[str, list[Any]] = {}
    for entry in entries:
        by_email.setdefault(entry.email, []).append(entry)

    for email, email_entries in by_email.items():
        email_entries.sort(key=lambda e: e.captured_at or e.created_at, reverse=True)
        
        latest_entry = email_entries[0]
        latest_name = latest_entry.archive_path.name
        
        is_encrypted = latest_name.endswith(".gpg")
        suffix = ".tar.gz.gpg" if is_encrypted else ".tar.gz"
        expected_latest_name = f"{safe_label(email)}-latest-antigravity{suffix}"
        
        if latest_name != expected_latest_name:
            target_archive = backup_dir / expected_latest_name
            target_metadata = backup_dir / expected_latest_name.replace(suffix, ".metadata.json")
            
            src_archive = latest_entry.archive_path
            src_metadata = metadata_path_for_archive(src_archive)
            
            if dry_run:
                console.print(f"[dry-run] Would promote local backup {src_archive.name} to {expected_latest_name}")
            else:
                try:
                    console.print(f"[cyan]Promoting local backup {src_archive.name} to {expected_latest_name}...[/cyan]")
                    if src_archive.exists():
                        shutil.move(src_archive, target_archive)
                    if src_metadata.exists():
                        try:
                            meta_data = json.loads(src_metadata.read_text(encoding="utf-8"))
                            meta_data["archive_name"] = expected_latest_name
                            meta_data["archive_path"] = str(target_archive)
                            target_metadata.write_text(json.dumps(meta_data, indent=2, sort_keys=True), encoding="utf-8")
                            src_metadata.unlink()
                        except Exception:
                            shutil.move(src_metadata, target_metadata)
                except Exception as e:
                    console_stderr.print(f"[bold red]Failed to promote backup for {email}: {e}[/]")
            
            duplicates = email_entries[1:]
        else:
            duplicates = email_entries[1:]

        for dup in duplicates:
            archive = dup.archive_path
            metadata = metadata_path_for_archive(archive)
            
            if dry_run:
                console.print(f"[dry-run] Would delete local legacy duplicate: {archive.name}")
            else:
                try:
                    console.print(f"Deleting local legacy duplicate: {archive.name}...")
                    if archive.exists() or archive.is_symlink():
                        archive.unlink()
                    if metadata.exists():
                        metadata.unlink()
                except Exception as e:
                    console_stderr.print(f"[bold red]Failed to delete legacy duplicate {archive.name}: {e}[/]")


def deduplicate_cloud(bucket: Any, dry_run: bool = False) -> None:
    try:
        remote_files = list(bucket.ls(recursive=True))
    except Exception as e:
        console_stderr.print(f"[bold red]Failed to list remote files for deduplication: {e}[/]")
        return

    for file_version, _ in remote_files:
        name = file_version.file_name
        is_backup_or_meta = (
            name.endswith("-antigravity.tar.gz") or 
            name.endswith("-antigravity.tar.gz.gpg") or
            name.endswith("-antigravity.metadata.json")
        )
        is_latest = "-latest-antigravity." in name
        
        if is_backup_or_meta and not is_latest:
            if dry_run:
                console.print(f"[dry-run] Would delete cloud legacy duplicate: {name}")
                continue
            
            file_id = getattr(file_version, "id_", None) or getattr(file_version, "file_id", None)
            try:
                if file_id:
                    console.print(f"Deleting cloud legacy duplicate: {name}...")
                    bucket.delete_file_version(file_id, name)
                elif hasattr(bucket, "hide_file"):
                    console.print(f"Hiding cloud legacy duplicate: {name}...")
                    bucket.hide_file(name)
            except Exception as e:
                console_stderr.print(f"[bold red]Failed to delete cloud duplicate {name}: {e}[/]")


def sync_auto(
    backup_dir: Path,
    bucket_name: str,
    endpoint_url: str | None = None,
    access_key: str | None = None,
    secret_key: str | None = None,
    dry_run: bool = False,
) -> None:
    if not access_key or not secret_key:
        console_stderr.print("[bold red]Missing B2 credentials (KEY_ID or APP_KEY).[/]")
        return

    console.print("[cyan]Step 1: Deduplicating and upgrading local backups to the 'latest' standard...[/cyan]")
    deduplicate_and_upgrade_local(backup_dir, dry_run=dry_run)

    try:
        bucket = _get_b2_bucket(access_key, secret_key, bucket_name)
    except Exception as e:
        console_stderr.print(f"[bold red]Failed to connect to B2 bucket {bucket_name}: {e}[/]")
        return

    console.print("[cyan]Step 2: Cleaning cloud legacy duplicates from B2...[/cyan]")
    deduplicate_cloud(bucket, dry_run=dry_run)

    console.print("[cyan]Step 3: Pulling missing latest backups from cloud...[/cyan]")
    pull_backup(
        backup_dir=backup_dir,
        bucket_name=bucket_name,
        endpoint_url=endpoint_url,
        access_key=access_key,
        secret_key=secret_key,
        dry_run=dry_run,
    )

    console.print("[cyan]Step 4: Pushing missing local latest backups to cloud...[/cyan]")
    push_backup(
        backup_dir=backup_dir,
        bucket_name=bucket_name,
        endpoint_url=endpoint_url,
        access_key=access_key,
        secret_key=secret_key,
        dry_run=dry_run,
    )
    console.print("[green]Bidirectional sync and deduplication complete![/green]")
