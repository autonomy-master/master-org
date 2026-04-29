#!/usr/bin/env python3
"""Post a tweet to X (Twitter) via OAuth 1.0a.

Reads credentials from `<repo-root>/.env`. No external dependencies (uses only
the Python 3 standard library). Echoes the tweet URL on success, exits non-zero
with the API error body on failure.

Usage:
    ./scripts/post-to-x.py "tweet text"
    echo "tweet text" | ./scripts/post-to-x.py
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"
ENDPOINT = "https://api.x.com/2/tweets"

REQUIRED_KEYS = (
    "X_CONSUMER_KEY",
    "X_CONSUMER_SECRET",
    "X_ACCESS_TOKEN",
    "X_ACCESS_TOKEN_SECRET",
)


def load_env() -> None:
    if not ENV_FILE.exists():
        sys.exit(f"ERROR: env file not found at {ENV_FILE}")
    for raw in ENV_FILE.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def encode(value: str) -> str:
    return quote(str(value), safe="")


def build_signature(
    method: str,
    url: str,
    oauth_params: dict[str, str],
    consumer_secret: str,
    token_secret: str,
) -> str:
    sorted_pairs = sorted(oauth_params.items())
    param_string = "&".join(f"{encode(k)}={encode(v)}" for k, v in sorted_pairs)
    base_string = f"{method}&{encode(url)}&{encode(param_string)}"
    signing_key = f"{encode(consumer_secret)}&{encode(token_secret)}"
    digest = hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


def get_my_username() -> str | None:
    """Fetch the authenticated user's handle. Returns None on any failure;
    callers should fall back to the universal 'i' handle in that case.
    """
    url = "https://api.x.com/2/users/me"
    oauth_params = {
        "oauth_consumer_key": os.environ["X_CONSUMER_KEY"],
        "oauth_nonce": secrets.token_urlsafe(24).rstrip("=").replace("-", "").replace("_", ""),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": os.environ["X_ACCESS_TOKEN"],
        "oauth_version": "1.0",
    }
    signature = build_signature(
        "GET",
        url,
        oauth_params,
        os.environ["X_CONSUMER_SECRET"],
        os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    oauth_params["oauth_signature"] = signature
    auth_header = "OAuth " + ", ".join(
        f'{encode(k)}="{encode(v)}"' for k, v in sorted(oauth_params.items())
    )
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"Authorization": auth_header, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("data", {}).get("username")
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        return None


def post_tweet(text: str) -> dict:
    for required in REQUIRED_KEYS:
        if not os.environ.get(required):
            sys.exit(f"ERROR: {required} not set in .env")

    oauth_params = {
        "oauth_consumer_key": os.environ["X_CONSUMER_KEY"],
        "oauth_nonce": secrets.token_urlsafe(24).rstrip("=").replace("-", "").replace("_", ""),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": os.environ["X_ACCESS_TOKEN"],
        "oauth_version": "1.0",
    }

    signature = build_signature(
        "POST",
        ENDPOINT,
        oauth_params,
        os.environ["X_CONSUMER_SECRET"],
        os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    oauth_params["oauth_signature"] = signature

    auth_header = "OAuth " + ", ".join(
        f'{encode(k)}="{encode(v)}"' for k, v in sorted(oauth_params.items())
    )

    body = json.dumps({"text": text}).encode("utf-8")
    request = urllib.request.Request(
        ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Authorization": auth_header,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "master-org-bot/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        sys.stderr.write(f"X API HTTP {exc.code}: {exc.reason}\n{body_text}\n")
        sys.exit(2)
    except urllib.error.URLError as exc:
        sys.stderr.write(f"X API connection error: {exc}\n")
        sys.exit(3)


def main() -> None:
    load_env()

    if len(sys.argv) > 1 and sys.argv[1] not in ("-", ""):
        text = sys.argv[1]
    else:
        text = sys.stdin.read().rstrip()

    if not text:
        sys.exit("ERROR: empty tweet text")

    response = post_tweet(text)
    data = response.get("data", {})
    tweet_id = data.get("id")
    if not tweet_id:
        sys.stderr.write(f"Unexpected response: {response}\n")
        sys.exit(4)

    # Resolve the handle dynamically from the authenticated user. Falls back
    # to "i" (X's universal handle that resolves any tweet by ID) if /users/me
    # fails — the URL still works, only the displayed handle differs.
    handle = get_my_username() or "i"
    print(f"✓ Posted to X: https://x.com/{handle}/status/{tweet_id}")
    print(f"   tweet_id={tweet_id} length={len(text)} chars")


if __name__ == "__main__":
    main()
