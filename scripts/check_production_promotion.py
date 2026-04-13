#!/usr/bin/env python3
"""Validate staging/main promotion rules for production profile."""

from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_ROOT = REPO_ROOT / "server"

EXPECTED_ROUTES = {
    "/production-soil-rainfall-index-with-urls",
    "/session/<session_id>/prefecture/<prefecture_code>",
    "/session/<session_id>/rainfall-data",
    "/session/<session_id>/recalculate",
    "/session/<session_id>/risk-at-time",
}

FORBIDDEN_PATTERNS = [
    "test_*.py",
    "server/tests/**/*.py",
    "**/__pycache__/**",
    "**/*.pyc",
    ".pytest_cache/**",
    "server/src/.pytest_cache/**",
]


def collect_routes() -> set[str]:
    os.environ["SOIL_RAINFALL_ROUTE_PROFILE"] = "production"
    sys.path.insert(0, str(SERVER_ROOT))

    import app  # pylint: disable=import-error,import-outside-toplevel

    return {
        rule.rule
        for rule in app.app.url_map.iter_rules()
        if rule.endpoint != "static"
    }


def collect_forbidden_files() -> list[str]:
    matches: set[str] = set()
    for pattern in FORBIDDEN_PATTERNS:
        for path in REPO_ROOT.glob(pattern):
            if path.is_file():
                matches.add(path.relative_to(REPO_ROOT).as_posix())
    return sorted(matches)


def main() -> int:
    actual_routes = collect_routes()
    missing_routes = sorted(EXPECTED_ROUTES - actual_routes)
    unexpected_routes = sorted(actual_routes - EXPECTED_ROUTES)
    forbidden_files = collect_forbidden_files()

    failed = False

    if missing_routes:
        failed = True
        print("Missing production routes:")
        for route in missing_routes:
            print(f"  - {route}")

    if unexpected_routes:
        failed = True
        print("Unexpected routes exposed in production profile:")
        for route in unexpected_routes:
            print(f"  - {route}")

    if forbidden_files:
        failed = True
        print("Forbidden files found in promotion payload:")
        for path in forbidden_files:
            print(f"  - {path}")

    if failed:
        return 1

    print("Production promotion checks passed.")
    for route in sorted(actual_routes):
        print(f"  - {route}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
