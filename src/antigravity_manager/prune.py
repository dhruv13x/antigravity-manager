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
    "log",
    "sessions",
    "brain",
    "conversations",
    "implicit",
]

CACHE_PRESERVED_NAMES = {
    "onboarding.json",
}


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

    cache_path = source_dir / "cache"
    if cache_path.exists() and any(
        item.name not in CACHE_PRESERVED_NAMES for item in cache_path.iterdir()
    ):
        directories.append(cache_path)

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
                    if item.name in CACHE_PRESERVED_NAMES:
                        continue
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
                continue
            shutil.rmtree(path)

    return plan


def prune_result_to_text(plan: PrunePlan, *, dry_run: bool, source_dir: Path | None = None) -> str:
    lines = [
        f"mode: {'dry-run' if dry_run else 'pruned'}",
    ]
    if source_dir is not None:
        lines.append(f"source_dir: {source_dir}")
    lines.append(f"files_removed: {len(plan.files)}")
    lines.extend(f"file: {path}" for path in plan.files)
    lines.append(f"directories_removed: {len(plan.directories)}")
    lines.extend(f"dir: {path}" for path in plan.directories)
    lines.append("preserved: authentication and persistent state")
    return "\n".join(lines)
