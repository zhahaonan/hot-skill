#!/usr/bin/env python3
"""
check_update — Compare local VERSION with upstream GitHub (no side effects except optional cache).
Exit 1 if upstream is newer (for CI/scripts); exit 0 if up-to-date or unreachable.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from _common import (
    VERSION,
    base_argparser,
    handle_schema,
    fetch_upstream_version,
    upstream_is_newer,
    UPSTREAM_REPO_URL,
    UPSTREAM_VERSION_URL,
)

SCHEMA = {
    "name": "check_update",
    "description": "Compare local VERSION with upstream GitHub. Exit 1 if newer available.",
    "input": {"type": "object", "properties": {}},
    "output": {
        "type": "object",
        "properties": {
            "local": {"type": "string"},
            "remote": {"type": "string"},
            "newer_available": {"type": "boolean"}
        }
    },
}


def main():
    parser = base_argparser("Compare local VERSION with upstream GitHub")
    args = parser.parse_args()
    handle_schema(args, SCHEMA)

    if os.environ.get("HOT_CREATOR_SKIP_UPDATE_CHECK", "").strip():
        print("HOT_CREATOR_SKIP_UPDATE_CHECK is set, skip.", file=sys.stderr)
        sys.exit(0)
    remote = fetch_upstream_version(timeout=5.0)
    print(f"local:   {VERSION}")
    print(f"check:   {UPSTREAM_VERSION_URL}")
    print(f"remote:  {remote or '(unreachable)'}")
    if remote and upstream_is_newer(VERSION, remote):
        print(
            f"\n有新版本。请更新: cd <skill目录> && git pull origin main\n"
            f"仓库: {UPSTREAM_REPO_URL}",
            file=sys.stderr,
        )
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
