#!/usr/bin/env bash
# Post a message to a Discord channel via webhook.
# Usage:
#   ./scripts/post-to-discord.sh <channel-key> "message"
#   echo "message" | ./scripts/post-to-discord.sh <channel-key>
#   cat file.md | ./scripts/post-to-discord.sh <channel-key>
#
# Channels (defined in .discord-webhooks.json at repo root):
#   morning, secretary, writing, money, master
#
# Auto-chunks messages over Discord's 2000-char limit on newline boundaries.

set -euo pipefail

CHANNEL="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEBHOOK_FILE="${SCRIPT_DIR}/../.discord-webhooks.json"

if [[ -z "$CHANNEL" ]]; then
  echo "Usage: $0 <channel-key> [message]" >&2
  echo "  channels: morning, secretary, writing, money, master" >&2
  exit 1
fi

if [[ ! -f "$WEBHOOK_FILE" ]]; then
  echo "ERROR: Webhook config not found at $WEBHOOK_FILE" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required. Install with: brew install jq" >&2
  exit 1
fi

URL=$(jq -r --arg ch "$CHANNEL" '.[$ch] // empty' "$WEBHOOK_FILE")
if [[ -z "$URL" || "$URL" == TBD-* ]]; then
  echo "ERROR: webhook for '$CHANNEL' not configured (value: ${URL:-empty})" >&2
  echo "  Update $WEBHOOK_FILE with a valid webhook URL." >&2
  exit 2
fi

# Source message: $2 if provided, else stdin
if [[ -n "${2:-}" ]]; then
  MESSAGE="$2"
else
  MESSAGE=$(cat)
fi

if [[ -z "$MESSAGE" ]]; then
  echo "ERROR: empty message" >&2
  exit 1
fi

post_chunk() {
  local chunk="$1"
  local payload
  payload=$(jq -n --arg content "$chunk" '{content: $content, allowed_mentions: {parse: []}}')
  if ! curl -sf -X POST "$URL" \
      -H "Content-Type: application/json" \
      -d "$payload" \
      -o /dev/null; then
    echo "ERROR: post to #$CHANNEL failed" >&2
    return 1
  fi
}

# Discord max content length is 2000 chars; use 1900 for safety.
LIMIT=1900
chunks_posted=0

if [[ ${#MESSAGE} -le $LIMIT ]]; then
  post_chunk "$MESSAGE"
  chunks_posted=1
else
  # Split on newlines, accumulating into chunks up to LIMIT.
  buffer=""
  while IFS= read -r line || [[ -n "$line" ]]; do
    candidate="${buffer}${line}"$'\n'
    if [[ ${#candidate} -gt $LIMIT ]]; then
      if [[ -n "$buffer" ]]; then
        post_chunk "$buffer"
        chunks_posted=$((chunks_posted + 1))
        # Tiny delay to respect rate limits when chunking
        sleep 0.3
      fi
      buffer="${line}"$'\n'
    else
      buffer="$candidate"
    fi
  done <<< "$MESSAGE"
  if [[ -n "$buffer" ]]; then
    post_chunk "$buffer"
    chunks_posted=$((chunks_posted + 1))
  fi
fi

echo "✓ Posted to #${CHANNEL} (${chunks_posted} message(s), ${#MESSAGE} chars)"
