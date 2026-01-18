import json
import requests
import uuid
from datetime import datetime


LICHESS_API = "https://lichess.org/api/games/user"

def extract_game_id_from_pgn(pgn_text: str):
    for line in pgn_text.splitlines():
        if line.startswith("[Site "):
            try:
                url = line.split('"')[1]
                return url.split("/")[-1]
            except:
                pass
    return str(uuid.uuid4())  # fallback for missing headers


def extract_datetime_from_pgn(pgn_text: str):
    date = None
    time = "00:00:00"

    for line in pgn_text.splitlines():
        if line.startswith("[UTCDate "):
            date = line.split('"')[1]
        elif line.startswith("[UTCTime "):
            time = line.split('"')[1]

    if date:
        try:
            return datetime.fromisoformat(f"{date}T{time}")
        except:
            pass

    return datetime.utcnow()  # fallback

def lichess_user_exists(username: str) -> bool:
    r = requests.get(
        f"https://lichess.org/api/user/{username}",
        timeout=5
    )
    return r.status_code == 200


def fetch_recent_pgns(username: str, count: int = 5):
    url = f"{LICHESS_API}/{username}"

    params_pgn = {"max": count, "moves": True}
    params_json = {
        "max": count,
        "pgnInJson": True,
        "clocks": False,
        "evals": False,
        "opening": True,
    }

    headers_pgn = {"Accept": "application/x-chess-pgn"}
    headers_json = {"Accept": "application/x-ndjson"}

    try:
        # Request PGN text blob
        res_pgn = requests.get(url, params=params_pgn, headers=headers_pgn, timeout=10)
        if res_pgn.status_code != 200:
            print("⚠️ PGN fetch failed:", res_pgn.status_code)
            return []

        pgn_blob = res_pgn.text.strip()
        raw_pgns = [chunk for chunk in pgn_blob.split("\n\n\n") if "[Event" in chunk]

        if not raw_pgns:
            print("ℹ️ No PGN games found")
            return []

        # Request JSON metadata
        res_json = requests.get(url, params=params_json, headers=headers_json, timeout=10)
        if res_json.status_code != 200:
            print("⚠️ Metadata fetch failed:", res_json.status_code)
            # fallback: still return PGN only
            return [{"id": None, "createdAt": None, "pgn": pgn} for pgn in raw_pgns[:count]]

        json_lines = res_json.text.strip().splitlines()

        games = []
        for i, line in enumerate(json_lines):
            try:
                meta = json.loads(line)
            except json.JSONDecodeError:
                continue  # skip corrupted line

            game_id = meta.get("id")
            created = meta.get("createdAt")

            if i < len(raw_pgns):
                games.append({
                    "id": game_id or f"fallback-{i}",
                    "createdAt": created,
                    "pgn": raw_pgns[i]
                })

        return games[:count]

    except Exception as err:
        print("🔥 Unexpected bootstrap error:", err)
        return []
