from __future__ import annotations

import os
import sys
from typing import Any

import requests
from rich.console import Console

console = Console()
console_stderr = Console(stderr=True)


def load_env_file(path: str) -> dict[str, str]:
    """Simple parsing of key=value env file."""
    if not os.path.exists(path):
        return {}
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                # simple unquote
                value = value.strip().strip("'").strip('"')
                env[key.strip()] = value
    except Exception:
        pass
    return env


def get_doppler_token() -> str | None:
    """
    Look for DOPPLER_TOKEN in:
    1. Environment Variables
    2. doppler.env
    3. .env
    """
    # 1. Environment
    token = os.environ.get("DOPPLER_TOKEN")
    if token:
        return token

    # 2. doppler.env
    d_env = load_env_file("doppler.env")
    if "DOPPLER_TOKEN" in d_env:
        return d_env["DOPPLER_TOKEN"]

    # 3. .env
    dot_env = load_env_file(".env")
    if "DOPPLER_TOKEN" in dot_env:
        return dot_env["DOPPLER_TOKEN"]

    return None


def fetch_doppler_secrets(token: str) -> dict[str, Any] | None:
    """Fetch secrets from Doppler API using the token."""
    url = "https://api.doppler.com/v3/configs/config/secrets/download?format=json"
    try:
        response = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            console_stderr.print(
                f"[yellow]Warning:[/] Found DOPPLER_TOKEN but failed to fetch secrets (Status: {response.status_code})."
            )
    except Exception as e:
        console_stderr.print(
            f"[yellow]Warning:[/] Found DOPPLER_TOKEN but failed to connect to Doppler: {e}"
        )
    return None


def resolve_credentials(
    args: Any, allow_fail: bool = False
) -> tuple[str | None, str | None, str | None, str | None]:
    """
    Resolve B2/S3 credentials (key_id, app_key, bucket_name, endpoint_url) with the following priority:
    1. CLI Arguments
    2. Doppler (DOPPLER_TOKEN in Env -> doppler.env -> .env)
    3. Environment Variables (AGM_B2_... or AWS_...)
    4. .env file
    """
    # 1. CLI Args
    c_id = getattr(args, "access_key", None)
    c_key = getattr(args, "secret_key", None)
    c_bucket = getattr(args, "bucket_name", None)
    c_endpoint = getattr(args, "endpoint_url", None)

    if c_id and c_key and c_bucket:
        return c_id, c_key, c_bucket, c_endpoint

    def fill_from(source_dict: dict[str, Any]) -> bool:
        nonlocal c_id, c_key, c_bucket, c_endpoint
        updated = False
        # Try AGM_B2 first
        if not c_id:
            c_id = source_dict.get("AGM_B2_KEY_ID") or source_dict.get("AWS_ACCESS_KEY_ID")
            if c_id:
                updated = True
        if not c_key:
            c_key = source_dict.get("AGM_B2_APP_KEY") or source_dict.get("AWS_SECRET_ACCESS_KEY")
            if c_key:
                updated = True
        if not c_bucket:
            c_bucket = source_dict.get("AGM_B2_BUCKET") or source_dict.get("AWS_BUCKET_NAME")
            if c_bucket:
                updated = True
        if not c_endpoint:
            c_endpoint = source_dict.get("AGM_B2_ENDPOINT") or source_dict.get("AWS_ENDPOINT_URL")
            if c_endpoint:
                updated = True
        return updated

    # 2. Doppler
    token = get_doppler_token()
    if token:
        secrets = fetch_doppler_secrets(token)
        if secrets:
            fill_from(secrets)

    if c_id and c_key and c_bucket:
        return c_id, c_key, c_bucket, c_endpoint

    # 3. Environment Variables
    fill_from(dict(os.environ))

    if c_id and c_key and c_bucket:
        return c_id, c_key, c_bucket, c_endpoint

    # 4. .env File
    dot_env_data = load_env_file(".env")
    fill_from(dot_env_data)

    if c_id and c_key and c_bucket:
        return c_id, c_key, c_bucket, c_endpoint

    if allow_fail:
        return c_id, c_key, c_bucket, c_endpoint

    console_stderr.print("[bold red]Error:[/] Missing B2/S3 credentials or bucket name.")
    console_stderr.print("Please provide credentials via any of these methods:")
    console_stderr.print("  1. Doppler (DOPPLER_TOKEN in env/doppler.env/.env)")
    console_stderr.print(
        "  2. Environment Variables (AGM_B2_KEY_ID, AGM_B2_APP_KEY, AGM_B2_BUCKET)"
    )
    console_stderr.print("  3. .env file in current directory")
    console_stderr.print("  4. CLI flags (--access-key, --secret-key, --bucket-name)")
    sys.exit(1)
