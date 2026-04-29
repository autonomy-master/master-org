#!/usr/bin/env python3
"""Fetch X (Twitter) metrics for the authenticated user and tracked tweet IDs.

Outputs a single JSON document on stdout with user public_metrics and
each tracked tweet's public_metrics. Reads OAuth 1.0a credentials from
`<repo-root>/.env`. Stdlib only (urllib + hmac).

Usage:
    ./scripts/fetch-x-metrics.py
    ./scripts/fetch-x-metrics.py --append-history    # also append to .metrics-history.jsonl
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
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"
HISTORY_FILE = REPO_ROOT / ".company" / "secretary" / ".metrics-history.jsonl"

# Tweet IDs we want to track over time. Add new IDs as the loop posts them.
TRACKED_TWEETS = {
    "2049418481226207291": "tweet1_account_intro",
    "2049420232260022539": "tweet2_article_announce",
    "2049434036100333910": "tweet3_serial_title",
}


def load_env() -> None:
    if not ENV_FILE.exists():
        sys.exit(f"ERROR: env file not found at {ENV_FILE}")
    for raw in ENV_FILE.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def encode(value) -> str:
    return urllib.parse.quote(str(value), safe="")


def oauth_request(method: str, url: str, query_params: dict[str, str] | None = None) -> dict:
    query_params = query_params or {}
    oauth_params = {
        "oauth_consumer_key": os.environ["X_CONSUMER_KEY"],
        "oauth_nonce": secrets.token_urlsafe(24).rstrip("=").replace("-", "").replace("_", ""),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": os.environ["X_ACCESS_TOKEN"],
        "oauth_version": "1.0",
    }
    # Combined params for signing
    all_params = {**query_params, **oauth_params}
    sorted_pairs = sorted(all_params.items())
    param_string = "&".join(f"{encode(k)}={encode(v)}" for k, v in sorted_pairs)
    base_string = f"{method}&{encode(url)}&{encode(param_string)}"
    signing_key = f"{encode(os.environ['X_CONSUMER_SECRET'])}&{encode(os.environ['X_ACCESS_TOKEN_SECRET'])}"
    signature = base64.b64encode(
        hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    ).decode()
    oauth_params["oauth_signature"] = signature

    auth_header = "OAuth " + ", ".join(
        f'{encode(k)}="{encode(v)}"' for k, v in sorted(oauth_params.items())
    )

    full_url = url
    if query_params:
        full_url = f"{url}?{urllib.parse.urlencode(query_params)}"

    req = urllib.request.Request(
        full_url,
        method=method,
        headers={"Authorization": auth_header, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        sys.stderr.write(f"X API HTTP {exc.code}: {exc.reason}\n{body_text}\n")
        sys.exit(2)


def main() -> None:
    load_env()
    out: dict = {"fetched_at": int(time.time()), "fetched_iso": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime())}

    # User metrics
    user_resp = oauth_request(
        "GET",
        "https://api.x.com/2/users/me",
        {"user.fields": "public_metrics,created_at"},
    )
    user = user_resp.get("data", {})
    out["user"] = {
        "username": user.get("username"),
        "id": user.get("id"),
        "metrics": user.get("public_metrics", {}),
    }

    # Tweet metrics (batch endpoint accepts comma-separated IDs, max 100)
    if TRACKED_TWEETS:
        tweets_resp = oauth_request(
            "GET",
            "https://api.x.com/2/tweets",
            {"ids": ",".join(TRACKED_TWEETS.keys()), "tweet.fields": "public_metrics,created_at"},
        )
        out["tweets"] = []
        for tweet in tweets_resp.get("data", []):
            out["tweets"].append(
                {
                    "id": tweet.get("id"),
                    "label": TRACKED_TWEETS.get(tweet.get("id"), "unknown"),
                    "created_at": tweet.get("created_at"),
                    "metrics": tweet.get("public_metrics", {}),
                }
            )

    # Optional: append to history JSONL for trend analysis
    if "--append-history" in sys.argv[1:]:
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with HISTORY_FILE.open("a") as f:
            f.write(json.dumps(out, ensure_ascii=False) + "\n")

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
