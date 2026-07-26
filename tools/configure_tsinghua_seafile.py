from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

import httpx


DEFAULT_BASE_URL = "https://cloud.tsinghua.edu.cn"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Exchange a Tsinghua Seafile login for an API token and configure local .env."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--env-file", type=Path, default=Path(__file__).resolve().parents[1] / ".env")
    parser.add_argument("--repo-name", default="Research Agent")
    parser.add_argument("--remote-root", default="research-agent")
    args = parser.parse_args()

    username = input("Tsinghua cloud username: ").strip()
    if not username:
        print("Username is required.", file=sys.stderr)
        return 2
    password = getpass.getpass("Tsinghua cloud password (hidden): ")
    if not password:
        print("Password is required.", file=sys.stderr)
        return 2

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{args.base_url.rstrip('/')}/api2/auth-token/",
                data={"username": username, "password": password},
            )
            response.raise_for_status()
            token = str(response.json().get("token", "")).strip()
    except httpx.HTTPStatusError as exc:
        print(
            f"Token exchange failed with HTTP {exc.response.status_code}. "
            "The university account may require SSO or an app-specific password.",
            file=sys.stderr,
        )
        return 1
    except (httpx.HTTPError, ValueError) as exc:
        print(f"Token exchange failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        password = ""

    if not token:
        print("Seafile did not return an API token.", file=sys.stderr)
        return 1

    updates = {
        "CLOUD_SYNC_ENABLED": "true",
        "SEAFILE_BASE_URL": args.base_url.rstrip("/"),
        "SEAFILE_API_TOKEN": token,
        "SEAFILE_USERNAME": "",
        "SEAFILE_PASSWORD": "",
        "SEAFILE_REPO_NAME": args.repo_name,
        "SEAFILE_REMOTE_ROOT": args.remote_root,
        "SEAFILE_SHARE_LINKS": "true",
    }
    _update_env(args.env_file, updates)
    try:
        os.chmod(args.env_file, 0o600)
    except OSError:
        pass
    print(f"Configured Seafile API token in {args.env_file}")
    print("Restart the research-agent service, then use the cloud sync button in /chat.")
    return 0


def _update_env(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(updates)
    output: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            output.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in remaining:
            output.append(f"{key}={remaining.pop(key)}")
        else:
            output.append(line)
    if remaining and output and output[-1].strip():
        output.append("")
    output.extend(f"{key}={value}" for key, value in remaining.items())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
