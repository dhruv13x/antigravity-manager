from __future__ import annotations

import os
import shutil
import urllib.request
from pathlib import Path
from typing import Any

from .credentials import resolve_credentials
from .sync import verify_cloud_connectivity


def run_doctor(
    *, antigravity_home: Path, gemini_home: Path, backup_dir: Path, args: Any = None
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
        ("gemini_home", gemini_home, str(gemini_home)),
        ("backup_dir", backup_dir, str(backup_dir)),
    ]
    for name, path, detail in dirs:
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
        checks.append(("Cloud (B2)", cloud_ok, f"Authenticated (Bucket: {bucket_name})" if cloud_ok else f"Failed (Bucket: {bucket_name})"))
    else:
        checks.append(("Cloud (B2)", False, "No bucket configured"))

    return checks


def print_doctor_table(checks: list[tuple[str, bool, str]]) -> None:
    from .ui import create_table, print_info, print_success, print_panel, console

    print_info("🩺 Running System Diagnostic...")

    table = create_table("Component", "Status", "Detail", title="System Diagnostic Results")

    for name, ok, detail in checks:
        status_text = "[success]✓ OK[/]" if ok else "[error]✗ FAIL[/]"
        table.add_row(name, status_text, f"[muted]{detail}[/]")

    print_panel(table, style="info")
    print_success("Diagnostic Complete.")
