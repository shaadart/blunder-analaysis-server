#!/usr/bin/env python3
"""Fetch recent games for a lichess user and save NDJSON/JSON output.

Usage examples:
  python3 fetch_lichess_games.py --username myusername --max 50
  python3 fetch_lichess_games.py --username myusername --since-days 7 --token <your_token>

The script uses the Lichess API endpoint: https://lichess.org/api/games/user/{username}
It requests NDJSON (one JSON object per line) and writes both NDJSON and a combined JSON file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Optional

import requests


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fetch recent games from Lichess for a user and save NDJSON/JSON.")
    p.add_argument("--username", required=True, help="Lichess username to fetch games for")
    p.add_argument("--token", help="Optional Lichess API token for authenticated requests (use Bearer)")
    p.add_argument("--max", type=int, default=100, help="Maximum number of games to fetch (default: 100)")
    p.add_argument("--since-days", type=int, default=0, help="Only fetch games since N days ago (0 = no since)")
    p.add_argument("--output-dir", default="output", help="Directory to save output files (default: ./output)")
    p.add_argument("--timeout", type=float, default=30.0, help="Request timeout in seconds")
    p.add_argument("--user-agent", default="fetch-lichess-games/1.0 (+https://lichess.org)", help="User-Agent header")
    return p.parse_args()


def fetch_games(username: str, token: Optional[str], max_games: int, since_ms: Optional[int], timeout: float, user_agent: str):
    url = f"https://lichess.org/api/games/user/{username}"
    headers = {"Accept": "application/x-ndjson", "User-Agent": user_agent}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    params = {"max": str(max_games)}
    if since_ms:
        params["since"] = str(since_ms)

    resp = requests.get(url, headers=headers, params=params, stream=True, timeout=timeout)

    if resp.status_code == 200:
        # stream NDJSON: one JSON object per line
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                # If parsing fails, yield raw line to allow inspection
                yield None, line
                continue
            yield obj, None
    elif resp.status_code == 401:
        raise RuntimeError("401 Unauthorized: check your API token or permissions")
    elif resp.status_code == 429:
        raise RuntimeError("429 Too Many Requests: rate limited by Lichess")
    else:
        raise RuntimeError(f"Unexpected status {resp.status_code}: {resp.text}")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def main() -> int:
    args = parse_args()
    since_ms = None
    if args.since_days and args.since_days > 0:
        since_dt = datetime.utcnow() - timedelta(days=args.since_days)
        since_ms = int(since_dt.timestamp() * 1000)

    ensure_dir(args.output_dir)
    now_ts = int(time.time())
    basefn = f"{args.username}_games_{now_ts}"
    ndjson_path = os.path.join(args.output_dir, basefn + ".ndjson")
    json_path = os.path.join(args.output_dir, basefn + ".json")

    games = []
    raw_lines = []
    count = 0
    print(f"Fetching up to {args.max} games for user '{args.username}'...")
    try:
        for obj, raw in fetch_games(args.username, args.token, args.max, since_ms, args.timeout, args.user_agent):
            if obj is None:
                raw_lines.append(raw)
            else:
                games.append(obj)
            count += 1
    except Exception as exc:
        print(f"Error fetching games: {exc}")
        return 2

    # Save NDJSON: use original JSON lines if available else dump from parsed objects
    with open(ndjson_path, "w", encoding="utf-8") as f:
        # prefer writing parsed objects for consistency
        for g in games:
            f.write(json.dumps(g, ensure_ascii=False) + "\n")
        # append any raw lines that failed to parse
        for r in raw_lines:
            f.write(r.rstrip() + "\n")

    # Save combined JSON list
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(games, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(games)} parsed games to: {ndjson_path} and {json_path}")
    if raw_lines:
        print(f"Additionally saved {len(raw_lines)} raw lines (parse failures preserved).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
