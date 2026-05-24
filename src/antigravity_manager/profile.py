from __future__ import annotations

import shutil
import tarfile
from pathlib import Path

from .config import AGM_HOME


def export_profile(export_path: Path, dry_run: bool = False) -> None:
    if not AGM_HOME.exists():
        raise FileNotFoundError(f"Antigravity manager home not found: {AGM_HOME}")

    from .ui import console

    if dry_run:
        console.print(f"Would export profile from {AGM_HOME} to {export_path}")
        return

    export_path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(export_path, "w:gz") as tar:
        tar.add(AGM_HOME, arcname=".")


def import_profile(import_path: Path, dry_run: bool = False) -> None:
    if not import_path.exists():
        raise FileNotFoundError(f"Profile archive not found: {import_path}")

    from .ui import console

    if dry_run:
        console.print(f"Would import profile from {import_path} to {AGM_HOME}")
        if AGM_HOME.exists():
            backup_path = AGM_HOME.with_name(f"{AGM_HOME.name}.bak")
            console.print(f"Would backup existing profile to {backup_path}")
        return

    # Backup existing first if it exists
    if AGM_HOME.exists():
        backup_path = AGM_HOME.with_name(f"{AGM_HOME.name}.bak")
        if backup_path.exists():
            shutil.rmtree(backup_path)
        shutil.move(AGM_HOME, backup_path)
        console.print(f"Backed up existing profile to {backup_path}")

    with tarfile.open(import_path, "r:gz") as tar:
        # Extract into parent directory since the archive contains the root folder
        AGM_HOME.mkdir(parents=True, exist_ok=True)
        tar.extractall(path=AGM_HOME, filter="data")
