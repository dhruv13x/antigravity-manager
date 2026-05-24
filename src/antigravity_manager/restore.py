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
from .utils import safe_label


def read_active_email(antigravity_home: Path) -> str | None:
    try:
        data = json.loads((antigravity_home / "google_accounts.json").read_text(encoding="utf-8"))
    except Exception:
        return None
    active = data.get("active")
    return active.strip() if isinstance(active, str) and active.strip() else None


def latest_backup_archive(backup_dir: Path, *, email: str | None = None) -> Path:
    entries = list_backups(backup_dir, email=email, latest_per_email=True)
    if not entries:
        suffix = f" for {email}" if email else ""
        raise FileNotFoundError(f"No Antigravity backup found{suffix} in: {backup_dir}")
    return entries[0].archive_path


def resolve_archive_path(args: Any) -> Path:
    if getattr(args, "from_archive", None):
        archive_path = Path(args.from_archive).expanduser()
    elif getattr(args, "email", None):
        latest_link = Path(args.backup_dir).expanduser() / f"{args.email}-latest-antigravity.tar.gz"
        archive_path = (
            latest_link
            if latest_link.exists()
            else latest_backup_archive(Path(args.backup_dir).expanduser(), email=args.email)
        )
    else:
        archive_path = latest_backup_archive(Path(args.backup_dir).expanduser())
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
        shutil.copytree(path, backup_path)
    else:
        shutil.copy2(path, backup_path)
    return backup_path


def copy_member_file(src: Path, dest: Path, *, dry_run: bool) -> Path | None:
    if not src.exists():
        return None
    if dry_run:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    backup_existing_file(dest, label="auth")
    if src.is_dir() and not src.is_symlink():
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
    else:
        shutil.copy2(src, dest)
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

    email = read_active_email(antigravity_home) or "unknown"
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    snapshot_dir = SAFETY_BACKUP_DIR / f"{timestamp}-{safe_label(email)}-pre-restore-antigravity"
    snapshot_dir.mkdir(parents=True, exist_ok=False)

    if antigravity_home.exists():
        shutil.copytree(
            antigravity_home,
            snapshot_dir / "antigravity-cli",
            symlinks=True,
            ignore=shutil.ignore_patterns("log", "updater", "knowledge"),
        )

    return snapshot_dir


def restore_full(
    extracted_dir: Path, antigravity_home: Path, *, dry_run: bool, force: bool
) -> Path | None:
    src = extracted_dir / "antigravity-cli"
    if not src.exists():
        raise ValueError("Archive does not contain antigravity-cli state.")
    if dry_run:
        return None
    antigravity_home.parent.mkdir(parents=True, exist_ok=True)
    safety_path = None
    if antigravity_home.exists():
        if not force:
            SAFETY_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
            safety_path = (
                SAFETY_BACKUP_DIR
                / f"antigravity-cli.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            )
            shutil.move(str(antigravity_home), str(safety_path))
        else:
            shutil.rmtree(antigravity_home)
    shutil.copytree(src, antigravity_home)
    restore_auth_only(extracted_dir, antigravity_home, dry_run=False)
    return safety_path


def perform_restore(args: Any) -> tuple[Path, dict[str, Any], list[Path], Path | None]:
    archive_path = resolve_archive_path(args)
    metadata = load_metadata_for_archive(archive_path)
    antigravity_home = Path(args.dest_dir).expanduser()

    with tempfile.TemporaryDirectory(prefix="agm-restore-") as temp_dir_str:
        extracted_dir = Path(temp_dir_str)
        safe_extract(archive_path, extracted_dir)
        pre_restore_snapshot = snapshot_current_state(
            antigravity_home=antigravity_home,
            dry_run=getattr(args, "dry_run", False),
        )
        if getattr(args, "full", False):
            safety_path = restore_full(
                extracted_dir,
                antigravity_home,
                dry_run=getattr(args, "dry_run", False),
                force=getattr(args, "force", False),
            )
            return archive_path, metadata, [], safety_path or pre_restore_snapshot
        restored = restore_auth_only(
            extracted_dir,
            antigravity_home,
            dry_run=getattr(args, "dry_run", False),
        )
        return archive_path, metadata, restored, pre_restore_snapshot


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
