from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict


DEFAULT_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def load_env_file(path: Path) -> Dict[str, str]:
    """Load key-value pairs from .env style file."""
    if not path.exists():
        raise FileNotFoundError(f".env file not found at {path}")

    env: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        env[key] = value
    return env


def update_env_file(path: Path, key: str, value: str) -> None:
    """Persist updated key-value into .env file (preserve existing lines when possible)."""
    lines = []
    replaced = False

    if path.exists():
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            stripped = raw_line.strip()
            if stripped.startswith(f"{key}="):
                quote_char = ""
                if len(stripped) > len(key) + 1 and stripped[len(key) + 1] in {'"', "'"}:
                    quote_char = stripped[len(key) + 1]
                if quote_char:
                    lines.append(f"{key}={quote_char}{value}{quote_char}")
                else:
                    lines.append(f"{key}={value}")
                replaced = True
            else:
                lines.append(raw_line)

    if not replaced:
        lines.append(f"{key}={value}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def http_request(url: str, *, method: str = "GET", data: dict | None = None, headers: dict | None = None) -> dict:
    """Perform an HTTP request and return JSON response."""
    request_data = None
    request_headers = headers.copy() if headers else {}

    if data is not None:
        request_data = json.dumps(data).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=request_data, headers=request_headers, method=method)

    try:
        with urllib.request.urlopen(req) as response:
            body = response.read().decode("utf-8")
            if not body:
                return {}
            return json.loads(body)
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8")
        raise RuntimeError(f"HTTP {exc.code} error for {url}: {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to reach {url}: {exc}") from exc


def ensure_trailing_slash_removed(url: str) -> str:
    return url.rstrip("/")


def perform_health_check(base_url: str, label: str) -> None:
    url = f"{ensure_trailing_slash_removed(base_url)}/health"
    response = http_request(url)
    status = response.get("status")
    if status != "ok":
        raise RuntimeError(f"{label} health check failed: {response}")
    print(f"[OK] {label} health check passed ({url})")


def refresh_summary_token(base_url: str, username: str, password: str) -> str:
    token_endpoint = f"{ensure_trailing_slash_removed(base_url)}/admin/token"
    response = http_request(
        token_endpoint,
        method="POST",
        data={"username": username, "password": password},
    )

    token = response.get("token")
    if not token:
        raise RuntimeError("Token response missing 'token' field.")

    print(f"[OK] Issued new summary token for admin '{response.get('admin', username)}'")
    return token


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render deployment helper for SEBIT APIs.")
    parser.add_argument(
        "--env",
        type=Path,
        default=DEFAULT_ENV_PATH,
        help="Path to .env file (default: project .env)",
    )
    parser.add_argument(
        "--refresh-token",
        action="store_true",
        help="Refresh SUMMARY_INTERNAL_TOKEN via /admin/token",
    )
    return parser.parse_args()


def _resolve_env_value(candidates: list[str], label: str) -> tuple[str, str]:
    """Return the first non-empty environment value among candidates."""
    for key in candidates:
        value = os.environ.get(key)
        if value:
            return value, key
    raise RuntimeError(f"Missing required environment variable for {label}: one of {', '.join(candidates)}")


def main() -> None:
    args = parse_args()
    env_path: Path = args.env

    env_vars = load_env_file(env_path)
    for key, value in env_vars.items():
        os.environ.setdefault(key, value)

    summary_base, _ = _resolve_env_value(
        ["SUMMARY_API_BASE_URL", "SUMMARY_BASE_URL", "SUMMARY_URL"],
        "Summary API base URL",
    )
    main_base = summary_base
    token_base: str | None = None
    try:
        main_base, _ = _resolve_env_value(
            ["MAIN_API_BASE_URL", "MAIN_BASE_URL", "MAIN_URL", "MAIN_API_URL"],
            "Main API base URL",
        )
        token_base = main_base
    except RuntimeError as exc:
        print(f"[WARN] {exc} – falling back to summary base URL for main API health checks.")

    perform_health_check(main_base, "Main API")
    perform_health_check(summary_base, "Summary API")

    if args.refresh_token:
        if token_base is None:
            raise RuntimeError(
                "MAIN_API_BASE_URL (or MAIN_BASE_URL/MAIN_URL/MAIN_API_URL) must be set to refresh the summary token."
            )

        username = os.getenv("ADMIN_USERNAME")
        password = os.getenv("ADMIN_PASSWORD")

        if not username or not password:
            raise RuntimeError("ADMIN_USERNAME and ADMIN_PASSWORD must be set to refresh the summary token.")

        new_token = refresh_summary_token(token_base, username, password)
        os.environ["SUMMARY_INTERNAL_TOKEN"] = new_token
        update_env_file(env_path, "SUMMARY_INTERNAL_TOKEN", new_token)
        print(f"[OK] SUMMARY_INTERNAL_TOKEN updated in environment and {env_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - CLI guard
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
