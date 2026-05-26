from __future__ import annotations

import json
import os
import shutil
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import (
    ANTIGRAVITY_AUTH_FILES,
    SAFETY_BACKUP_DIR,
)
from .list_backups import list_backups, load_metadata_for_archive
from .ui import RenderableType
from .utils import read_active_email, safe_label


def resolve_current_email(antigravity_home: Path) -> str:
    return read_active_email(antigravity_home) or "unknown"


def archive_directory(source_dir: Path, archive_path: Path, *, arcname: str | None = None) -> Path:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(source_dir, arcname=arcname or source_dir.name, recursive=True)
    return archive_path


def latest_backup_archive(backup_dir: Path, *, email: str | None = None) -> Path:
    entries = list_backups(backup_dir, email=email, latest_per_email=True)
    if not entries:
        suffix = f" for {email}" if email else ""
        raise FileNotFoundError(f"No Antigravity backup found{suffix} in: {backup_dir}")
    return entries[0].archive_path


def _is_archive_target(value: str) -> bool:
    return value.endswith(".tar.gz") or value.endswith(".tar.gz.gpg")


def resolve_target_archive(backup_dir: Path, target: str) -> Path:
    target_path = Path(target).expanduser()
    if target_path.exists() or _is_archive_target(target):
        archive_path = target_path
        if not archive_path.exists() and not archive_path.is_absolute():
            archive_path = backup_dir / target
        return archive_path

    latest_link = backup_dir / f"{target}-latest-antigravity.tar.gz"
    if latest_link.exists():
        return latest_link
    return latest_backup_archive(backup_dir, email=target)


def resolve_archive_path(args: Any) -> Path:
    backup_dir = Path(args.backup_dir).expanduser()
    target = getattr(args, "target", None)
    if target:
        archive_path = resolve_target_archive(backup_dir, target)
    elif getattr(args, "from_archive", None):
        archive_path = Path(args.from_archive).expanduser()
    elif getattr(args, "email", None):
        latest_link = backup_dir / f"{args.email}-latest-antigravity.tar.gz"
        archive_path = (
            latest_link
            if latest_link.exists()
            else latest_backup_archive(backup_dir, email=args.email)
        )
    else:
        archive_path = latest_backup_archive(backup_dir)
    if not archive_path.exists():
        raise FileNotFoundError(f"Backup archive does not exist: {archive_path}")
    return archive_path.resolve()


def validate_member_name(name: str) -> None:
    if name.startswith("/") or ".." in Path(name).parts:
        raise ValueError(f"Unsafe archive member path: {name}")
    if not (
        name.startswith("antigravity-cli/")
        or name.startswith("gemini/")
        or name.endswith(".metadata.json")
    ):
        raise ValueError(f"Unexpected archive member path: {name}")


def _link_stays_within_archive(member_name: str, link_name: str) -> bool:
    if os.path.isabs(link_name):
        return False
    member_parent = Path(member_name).parent
    target_parts = (member_parent / link_name).parts
    return ".." not in target_parts


def safe_tar_filter(member: tarfile.TarInfo, dest_path: str) -> tarfile.TarInfo | None:
    validate_member_name(member.name)
    if member.name.startswith("gemini/"):
        return None
    if member.islnk() or member.issym():
        if not _link_stays_within_archive(member.name, member.linkname):
            return None
    return tarfile.data_filter(member, dest_path)


def safe_extract(archive_path: Path, dest_dir: Path) -> None:
    if archive_path.suffix == ".gpg":
        import getpass
        import subprocess

        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as temp_archive:
            temp_path = Path(temp_archive.name)
            passphrase = os.environ.get("AGM_BACKUP_PASSWORD")
            if not passphrase:
                passphrase = getpass.getpass(f"Passphrase for {archive_path.name}: ")

            gpg_cmd = [
                "gpg",
                "--decrypt",
                "--passphrase-fd",
                "0",
                "--batch",
                "--yes",
                "--output",
                str(temp_path),
                str(archive_path),
            ]
            try:
                subprocess.run(gpg_cmd, input=passphrase.encode(), check=True)
                with tarfile.open(temp_path, "r:gz") as tar:
                    for member in tar.getmembers():
                        validate_member_name(member.name)
                    tar.extractall(dest_dir, filter=safe_tar_filter)
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                raise RuntimeError(f"GPG decryption failed: {e}") from e
    else:
        with tarfile.open(archive_path, "r:gz") as tar:
            for member in tar.getmembers():
                validate_member_name(member.name)
            tar.extractall(dest_dir, filter=safe_tar_filter)


def backup_existing_file(path: Path, *, label: str) -> Path | None:
    if not path.exists() and not path.is_symlink():
        return None
    SAFETY_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_name = f"{safe_label(label)}-{path.name}.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    backup_path = SAFETY_BACKUP_DIR / backup_name
    if path.is_dir() and not path.is_symlink():
        backup_path = backup_path.with_suffix(f"{backup_path.suffix}.tar.gz")
        archive_directory(path, backup_path, arcname=path.name)
    else:
        shutil.copy2(path, backup_path, follow_symlinks=False)
    return backup_path


def copy_member_file(src: Path, dest: Path, *, dry_run: bool) -> Path | None:
    if not src.exists() and not src.is_symlink():
        return None
    if dry_run:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir() and not src.is_symlink():
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest, symlinks=True)
    else:
        shutil.copy2(src, dest, follow_symlinks=False)
    return dest


def restore_auth_only(extracted_dir: Path, antigravity_home: Path, *, dry_run: bool) -> list[Path]:
    restored: list[Path] = []
    for name in ANTIGRAVITY_AUTH_FILES:
        dest = antigravity_home / name
        src = extracted_dir / "antigravity-cli" / name
        copied = copy_member_file(src, dest, dry_run=dry_run)
        if copied:
            restored.append(copied)
    return restored


def snapshot_current_state(
    *,
    antigravity_home: Path,
    dry_run: bool,
) -> Path | None:
    if dry_run:
        return None
    if not antigravity_home.exists():
        return None

    email = resolve_current_email(antigravity_home)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    snapshot_dir = SAFETY_BACKUP_DIR / f"{timestamp}-{safe_label(email)}-pre-restore-antigravity"
    snapshot_archive = snapshot_dir.with_name(f"{snapshot_dir.name}.tar.gz")
    snapshot_dir.mkdir(parents=True, exist_ok=False)

    if antigravity_home.exists():
        shutil.copytree(
            antigravity_home,
            snapshot_dir / "antigravity-cli",
            symlinks=True,
            ignore=shutil.ignore_patterns("log", "updater", "knowledge"),
        )

    archive_directory(snapshot_dir, snapshot_archive, arcname=snapshot_dir.name)
    shutil.rmtree(snapshot_dir)
    return snapshot_archive


def restore_full(extracted_dir: Path, antigravity_home: Path, *, dry_run: bool, force: bool) -> None:
    src = extracted_dir / "antigravity-cli"
    if not src.exists():
        raise ValueError("Archive does not contain antigravity-cli state.")
    if dry_run:
        return
    antigravity_home.parent.mkdir(parents=True, exist_ok=True)
    if antigravity_home.exists():
        shutil.rmtree(antigravity_home)
    shutil.copytree(src, antigravity_home, symlinks=True)


def perform_restore(args: Any) -> tuple[Path, dict[str, Any], list[Path], Path | None]:
    archive_path = resolve_archive_path(args)
    metadata = load_metadata_for_archive(archive_path)
    antigravity_home = Path(args.dest_dir).expanduser()

    with tempfile.TemporaryDirectory(prefix="agm-restore-") as temp_dir_str:
        extracted_dir = Path(temp_dir_str)
        safe_extract(archive_path, extracted_dir)
        safety_path = None
        if not (getattr(args, "full", False) and getattr(args, "force", False)):
            safety_path = snapshot_current_state(
                antigravity_home=antigravity_home,
                dry_run=getattr(args, "dry_run", False),
            )
        if getattr(args, "full", False):
            restore_full(
                extracted_dir,
                antigravity_home,
                dry_run=getattr(args, "dry_run", False),
                force=getattr(args, "force", False),
            )
            return archive_path, metadata, [], safety_path
        restored = restore_auth_only(
            extracted_dir,
            antigravity_home,
            dry_run=getattr(args, "dry_run", False),
        )
        return archive_path, metadata, restored, safety_path


def restore_result_to_text(
    archive_path: Path,
    metadata: dict[str, Any],
    restored_files: list[Path],
    safety_path: Path | None,
    *,
    dry_run: bool,
    full: bool,
) -> RenderableType:
    from .ui import Group, Panel, Table, Text, Tree

    title = "[warning]Restore Result (Dry Run)[/]" if dry_run else "[success]Restore Completed[/]"
    border_style = "warning" if dry_run else "success"

    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", justify="right")
    table.add_column(style="white")

    table.add_row("Email:", str(metadata.get("email", "unknown")))
    table.add_row("Plan:", str(metadata.get("plan", "unknown")))
    table.add_row("Type:", "Full Restore" if full else "Auth-only Restore")
    table.add_row("Archive:", str(archive_path))

    if safety_path:
        table.add_row("Safety Backup:", f"[dim]{safety_path}[/dim]")

    components = [table]

    if restored_files:
        tree = Tree("[bold bright_cyan]Restored Files[/]")
        for path in restored_files:
            tree.add(f"[green]{path}[/]")

        components.append(Text(""))
        components.append(tree)

    return Panel(Group(*components), title=title, border_style=border_style, expand=False)
