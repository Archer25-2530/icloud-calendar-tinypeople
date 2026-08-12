#!/usr/bin/env python3
"""
Generate precomputed digests for all bridge actions.

Run once after setting salt/key in config, then hardcode the
printed digests into your trigger URLs. Re-run if you rotate keys.

Usage:
    python3 generate_digests.py --base-url https://your-bridge-host.example
    ICLOUD_BRIDGE_BASE_URL=https://your-bridge-host.example python3 generate_digests.py
"""

import argparse
import hashlib
import json
import os
import sys

CONFIG_FILE = os.path.expanduser("~/.tinyPeople/conf/icloud-calendar/config.json")

READ_ACTION_PATHS = {
    "calendars": "/v1/calendars",
    "today":     "/v1/events/today",
    "upcoming":  "/v1/events/upcoming",
    "list":      "/v1/events/list",
}

WRITE_ACTION_PATHS = {
    "create": "/v1/events/create",
    "delete": "/v1/events/delete",
}


def _config_candidates():
    """Return possible config paths in priority order."""
    candidates = []

    # 1) Explicit override for runtimes where HOME differs.
    cfg_env = os.environ.get("ICLOUD_CALENDAR_CONFIG", "").strip()
    if cfg_env:
        candidates.append(cfg_env)

    # 2) Standard home-based config path.
    candidates.append(CONFIG_FILE)

    # 3) App-local fallback (useful for troubleshooting).
    candidates.append(os.path.join(os.path.dirname(__file__), "config.json"))

    # De-duplicate while preserving order.
    unique = []
    for path in candidates:
        if path and path not in unique:
            unique.append(path)
    return unique


def _resolve_config_path():
    for cfg_path in _config_candidates():
        if os.path.exists(cfg_path):
            return cfg_path
    return None


def resolve_base_url(cli_base_url: str, config: dict) -> str:
    if cli_base_url:
        return cli_base_url.rstrip("/")

    env_base_url = os.environ.get("ICLOUD_BRIDGE_BASE_URL", "").strip()
    if env_base_url:
        return env_base_url.rstrip("/")

    cfg_base_url = (
        config.get("bridge", {})
        .get("public_base_url", "")
        .strip()
    )
    if cfg_base_url:
        return cfg_base_url.rstrip("/")

    return ""


def compute_digest(salt: str, key: str, key_id: str, action: str, path: str) -> str:
    payload = f"{salt}:{key}:{key_id}:{action}:{path}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Generate bridge digests for all actions.")
    parser.add_argument(
        "--base-url",
        default="",
        help="Base URL of the bridge (or use ICLOUD_BRIDGE_BASE_URL / config bridge.public_base_url)",
    )
    args = parser.parse_args()
    config_path = _resolve_config_path()
    if not config_path:
        print(
            f"Error: Config not found. Checked candidates: {_config_candidates()}",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    base_url = resolve_base_url(args.base_url, config)
    if not base_url:
        print(
            "Error: Missing base URL. Set one of: --base-url, ICLOUD_BRIDGE_BASE_URL, or bridge.public_base_url in config.",
            file=sys.stderr,
        )
        sys.exit(1)

    read_keys = config.get("bridge", {}).get("read_auth", {}).get("keys", {})
    write_keys = config.get("bridge", {}).get("write_auth", {}).get("keys", {})
    if not read_keys and not write_keys:
        print("Error: No keys found in bridge.read_auth.keys or bridge.write_auth.keys", file=sys.stderr)
        sys.exit(1)

    for label, keys, action_paths in (
        ("read", read_keys, READ_ACTION_PATHS),
        ("write", write_keys, WRITE_ACTION_PATHS),
    ):
        for key_id, key_cfg in keys.items():
            salt = key_cfg.get("salt", "")
            key  = key_cfg.get("key",  "")
            if not salt or not key or "replace-with" in salt or "replace-with" in key:
                print(f"[{label}:{key_id}] Skipped — salt/key not set (still placeholder)")
                continue

            print(f"\n=== {label} key_id: {key_id} ===")
            for action, path in action_paths.items():
                digest = compute_digest(salt, key, key_id, action, path)
                url    = f"{base_url}{path}?action={action}&key_id={key_id}&digest={digest}"
                print(f"\n  {action}")
                print(f"    digest: {digest}")
                print(f"    url:    {url}")

    print()


if __name__ == "__main__":
    main()
