#!/usr/bin/env python3
"""Authentication helper for the notebooklm-research skill.

Thin wrapper around ``notebooklm.NotebookLMClient.from_storage()`` that turns
a missing/expired session into a clear, actionable error message instead of
a raw traceback. Every other script in this skill imports ``require_client``
from here rather than calling ``from_storage()`` directly.

Login itself is NOT handled here — it requires an interactive browser and
must be run by the human on their own machine:

    pip install "notebooklm-py[browser]"
    notebooklm login
    notebooklm login --check   # or: python3 auth_helper.py --check
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from contextlib import asynccontextmanager

try:
    from notebooklm import AuthError, MissingDependencyError, NotebookLMClient
except ImportError as exc:  # pragma: no cover - guidance path, not a bug
    sys.exit(
        "notebooklm-py is not installed.\n"
        "Install it with:  pip install notebooklm-py\n"
        f"(import failed: {exc})"
    )

LOGIN_HINT = (
    "No valid NotebookLM session found.\n"
    "Run this on a machine with a real browser (not this remote/headless session):\n"
    "  pip install \"notebooklm-py[browser]\"\n"
    "  notebooklm login\n"
    "Then verify with:\n"
    "  notebooklm login --check\n"
)


@asynccontextmanager
async def require_client(profile: str | None = None):
    """Yield an authenticated ``NotebookLMClient``, or exit with a clear message.

    Use exactly like ``NotebookLMClient.from_storage()``:

        async with require_client() as client:
            notebooks = await client.notebooks.list()
    """
    try:
        async with NotebookLMClient.from_storage(profile=profile) as client:
            yield client
    except FileNotFoundError:
        sys.exit(LOGIN_HINT)
    except MissingDependencyError as exc:
        sys.exit(f"Missing optional dependency: {exc}\nRun: pip install \"notebooklm-py[browser]\"")
    except AuthError as exc:
        sys.exit(f"{LOGIN_HINT}\n(auth error: {exc})")


async def check_session(profile: str | None = None) -> dict:
    """Return a small status dict without raising — used by --check and MCP tools."""
    try:
        async with NotebookLMClient.from_storage(profile=profile) as client:
            settings = await client.settings.get_user_settings()
            notebooks = await client.notebooks.list()
            return {
                "authenticated": True,
                "profile": profile or "default",
                "notebook_count": len(notebooks),
                "output_language": settings.output_language,
            }
    except FileNotFoundError:
        return {"authenticated": False, "profile": profile or "default", "reason": "no_stored_session"}
    except AuthError as exc:
        return {"authenticated": False, "profile": profile or "default", "reason": str(exc)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify the stored session is valid and exit")
    parser.add_argument("--profile", default=None, help="Profile name (default: the notebooklm CLI's active profile)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if not args.check:
        parser.print_help()
        sys.exit(1)

    status = asyncio.run(check_session(profile=args.profile))
    if args.json:
        print(json.dumps(status, indent=2))
    else:
        if status["authenticated"]:
            print(f"Authenticated (profile: {status['profile']}) — {status['notebook_count']} notebook(s) visible.")
        else:
            print(LOGIN_HINT)
    sys.exit(0 if status["authenticated"] else 1)


if __name__ == "__main__":
    main()
