from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

FILE_GLOBS = [
    "logs.json",
    "history.jsonl",
    "models_cache.json",
    "cli.log",
    "last_check.timestamp",
]

DIRECTORY_NAMES = [
    "tmp",
    ".tmp",
    "history",
    "cache",
    "log",
    "sessions",
    "brain",
    "conversations",
    "implicit",
]


@dataclass(frozen=True)
class PrunePlan:
    files: list[Path]
    directories: list[Path]


def build_prune_plan(source_dir: Path) -> PrunePlan:
    files: list[Path] = []
    directories: list[Path] = []

    for pattern in FILE_GLOBS:
        files.extend(sorted(source_dir.glob(pattern), key=lambda path: path.name))

    for name in DIRECTORY_NAMES:
        path = source_dir / name
        if path.exists():
            directories.append(path)

    return PrunePlan(files=files, directories=directories)


def perform_prune(args: Any) -> PrunePlan:
    source_dir = Path(args.source_dir).expanduser()
    if not source_dir.exists() or not source_dir.is_dir():
        raise FileNotFoundError(f"Antigravity CLI directory does not exist: {source_dir}")

    plan = build_prune_plan(source_dir)
    if args.dry_run:
        return plan

    for path in plan.files:
        if path.exists():
            path.unlink()

    for path in plan.directories:
        if path.exists():
            if path.name == "tmp":
                bin_path = path / "bin"
                if bin_path.exists():
                    for item in path.iterdir():
                        if item.name == "bin":
                            continue
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                    continue
            elif path.name == "cache":
                for item in path.iterdir():
                    if item.name == "onboarding.json":
                        continue
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                continue
            shutil.rmtree(path)

    return plan


def prune_result_to_text(plan: PrunePlan, *, dry_run: bool, source_dir: Path | None = None) -> str:
    from .ui import Table, print_panel, print_info
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Property", style="info")
    table.add_column("Value", style="muted")

    table.add_row("Mode", "[warning]DRY RUN[/]" if dry_run else "[success]PRUNED[/]")
    if source_dir is not None:
        table.add_row("Source Dir", str(source_dir))
    table.add_row("Files Removed", str(len(plan.files)))
    table.add_row("Directories Removed", str(len(plan.directories)))
    table.add_row("Preserved", "authentication and persistent state")

    print_panel(table, title="Prune Result", style="success")

    if plan.files:
        print_info("Files pruned:")
        for path in plan.files:
            print_info(f"  - {path}")
    if plan.directories:
        print_info("Directories pruned:")
        for path in plan.directories:
            print_info(f"  - {path}")

    return ""
