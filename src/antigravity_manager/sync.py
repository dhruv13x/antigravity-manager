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

    # Push all tar.gz and metadata.json files
    backup_files = sorted(
        list(backup_dir.glob("*.tar.gz")) + list(backup_dir.glob("*.metadata.json"))
    )

    for file_path in backup_files:
        if not file_path.is_file() or file_path.is_symlink():
            continue

        object_name = file_path.name

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
    local_files = {p.name for p in backup_dir.glob("*")}

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
                console.print(f"Downloading b2://{bucket_name}/{object_name} to {file_path}...")
                download_dest = bucket.download_file_by_name(object_name)
                download_dest.save_to(str(file_path))
                console.print(f"[green]Successfully downloaded {object_name}[/]")
            except Exception as e:
                console_stderr.print(f"[bold red]Failed to download {object_name}: {e}[/]")
    except Exception as e:
        console_stderr.print(f"[bold red]Failed to sync with bucket {bucket_name}: {e}[/]")


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
