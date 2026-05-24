from __future__ import annotations

import os
import shutil
import urllib.request
from pathlib import Path
from typing import Any

from .credentials import resolve_credentials
from .sync import verify_cloud_connectivity


def run_doctor(
    *, antigravity_home: Path, backup_dir: Path, args: Any = None
) -> list[tuple[str, bool, str]]:
    checks = []

    # Tools
    tools = ["agm", "tmux", "agy", "tar", "diff", "npm", "gpg"]
    for tool in tools:
        path = shutil.which(tool)
        checks.append((f"Tool: {tool}", path is not None, path or "missing"))

    # Directories
    dirs = [
        ("antigravity_home", antigravity_home, str(antigravity_home)),
        ("backup_dir", backup_dir, str(backup_dir)),
    ]
    for name, path, _ in dirs:
        if path.is_dir():
            if os.access(path, os.W_OK):
                checks.append((f"Dir: {name}", True, f"Writable: {path}"))
            else:
                checks.append((f"Dir: {name}", False, f"Read-only: {path}"))
        else:
            checks.append((f"Dir: {name}", False, f"Missing: {path}"))

    # Network
    try:
        urllib.request.urlopen("https://www.google.com", timeout=3)
        checks.append(("Network", True, "Internet accessible"))
    except Exception:
        checks.append(("Network", False, "No internet connection"))

    # Cloud Check
    access_key, secret_key, bucket_name, endpoint_url = resolve_credentials(args, allow_fail=True)
    if bucket_name:
        cloud_ok = verify_cloud_connectivity(
            bucket_name=bucket_name,
            endpoint_url=endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
        )
        checks.append(
            (
                "Cloud (B2)",
                cloud_ok,
                (
                    f"Authenticated (Bucket: {bucket_name})"
                    if cloud_ok
                    else f"Failed (Bucket: {bucket_name})"
                ),
            )
        )
    else:
        checks.append(("Cloud (B2)", False, "No bucket configured"))

    return checks


def print_doctor_table(checks: list[tuple[str, bool, str]]) -> None:
    from .banner import print_logo
    from .ui import Table, console

    print_logo()
    console.print("[bold cyan]Running System Diagnostic...[/]")

    table = Table(show_header=True, header_style="bold bright_magenta")
    table.add_column("Component", style="bright_cyan")
    table.add_column("Status", justify="center")
    table.add_column("Detail", style="dim")

    for name, ok, detail in checks:
        table.add_row(
            name,
            "[bold bright_green]OK[/]" if ok else "[bold red]FAIL[/]",
            detail,
        )
    console.print(table)
    console.print("[bold bright_green]Diagnostic Complete.[/]")
