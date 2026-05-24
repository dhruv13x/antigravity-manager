from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Group
from rich.text import Text

from .ui import Panel, render_dict_as_table

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


def prune_result_to_text(
    plan: PrunePlan, *, dry_run: bool, source_dir: Path | None = None
) -> Panel:
    title = (
        "[bold yellow]Dry Run: Prune Plan[/]"
        if dry_run
        else "[bold bright_green]Prune Completed[/]"
    )

    data: dict[str, Any] = {}
    if source_dir is not None:
        data["Source Dir"] = str(source_dir)

    data["Files Removed"] = str(len(plan.files))
    data["Directories Removed"] = str(len(plan.directories))
    data["Preserved"] = "Authentication and persistent state"

    table = render_dict_as_table(data)
    renderables = [table]

    if plan.files or plan.directories:
        details = Text("\nDetails:\n", style="bold cyan")
        for path in plan.files:
            details.append(f"  - {path}\n", style="dim")
        for path in plan.directories:
            details.append(f"  - {path}/\n", style="dim")
        renderables.append(details)

    return Panel(
        Group(*renderables),
        title=title,
        border_style="yellow" if dry_run else "bright_green",
        expand=False,
    )
