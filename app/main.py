from datetime import datetime, timezone
import uuid
import requests

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from psycopg2 import IntegrityError

from .pgn_analysis import analyze_pgn
from .bootstrap import bootstrap_analysis
from .models import User
from .db import get_db
from .crud import (
    create_game,
    create_user,
    get_game_by_id,
    get_pushups_due,
    get_pushups_forgiven,
    get_recent_games,
    username_exists,
    suggest_usernames,
)
from .utils import lichess_user_exists
from .schemas import SignupRequest


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

LICHESS_API = "https://lichess.org/api/games/user"

HEADERS = {
    "Accept": "application/x-chess-pgn",
    "User-Agent": "ChessPushups/1.0 (contact: dev@local)",
}

# ─────────────────────────────────────────────────────────────
# 🔓 PUBLIC: Analyze pasted PGN (NO DB USER REQUIRED)
# ─────────────────────────────────────────────────────────────

@app.post("/analyze-pgn")
def analyze_pgn_text(
    player: str,
    pgn: str = Body(..., media_type="text/plain"),
):
    player = player.strip().lower()
    pgn_text = normalize_pgn(pgn)

    if not pgn_text.strip():
        raise HTTPException(400, "PGN cannot be empty")

    if not player:
        raise HTTPException(400, "Player name is required")

    try:
        result = analyze_pgn(pgn_text, player)
    except ValueError as e:
        raise HTTPException(
            400,
            f"Player '{player}' not found in PGN headers",
        )
    except Exception:
        raise HTTPException(500, "Failed to analyze PGN")

    return result


# ─────────────────────────────────────────────────────────────
# Analyze latest Lichess game (DB user REQUIRED)
# ─────────────────────────────────────────────────────────────

@app.get("/analyze-latest-game")
def analyze_latest_game(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(404, "User not found")

    try:
        response = requests.get(
            f"{LICHESS_API}/{user.lichess_username}",
            params={"max": 1},
            headers=HEADERS,
            timeout=10,
        )
    except requests.exceptions.RequestException:
        raise HTTPException(503, "Lichess API temporarily unavailable")

    if response.status_code != 200 or not response.text.strip():
        raise HTTPException(204, "No games available yet")

    pgn_text = response.text

    try:
        result = analyze_pgn(pgn_text, user.username)
    except ValueError:
        raise HTTPException(204, "No analyzable game yet")

    game_id = extract_game_id(pgn_text) or str(uuid.uuid4())
    played_at = extract_played_at(pgn_text)

    if not get_game_by_id(db, game_id):
        create_game(
            db=db,
            game_id=game_id,
            user_id=user.id,
            played_at=played_at,
            mode=result["game_mode"],
            player_color=result["player_color"],
            opponent=result["opponent"],
            blunders=result["blunders"],
            pushups=result["pushups"],
            status="new",
        )

    return result


# ─────────────────────────────────────────────────────────────
# Username availability
# ─────────────────────────────────────────────────────────────

@app.get("/users/check-username")
def check_username(username: str, db: Session = Depends(get_db)):
    username = username.strip().lower()
    if not username:
        return {"available": False}

    if username_exists(db, username):
        return {"available": False, "suggestions": suggest_usernames(db, username)}

    return {"available": True}


# ─────────────────────────────────────────────────────────────
# Signup
# ─────────────────────────────────────────────────────────────

@app.post("/auth/signup")
def signup(
    payload: SignupRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    username = payload.username.strip().lower()
    lichess_user = payload.lichess_username.strip().lower()

    if not lichess_user_exists(lichess_user):
        raise HTTPException(400, "Lichess username does not exist")

    try:
        user = create_user(db, username, lichess_user)
        background_tasks.add_task(bootstrap_analysis, str(user.id))
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Username already taken")

    return {
        "id": str(user.id),
        "username": user.username,
        "lichess_username": user.lichess_username,
    }


# ─────────────────────────────────────────────────────────────
# Home
# ─────────────────────────────────────────────────────────────

@app.get("/home")
def home(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(404, "User not found")

    games = get_recent_games(db, user.id)

    return {
        "username": user.username,
        "pushups_due": get_pushups_due(db, user.id),
        "pushups_forgiven": get_pushups_forgiven(db, user.id),
        "games": [
            {
                "game_id": g.id,
                "played_at": g.played_at.isoformat(),
                "player_color": g.player_color,
                "opponent": g.opponent,
                "game_mode": g.mode,
                "blunders": g.blunders,
                "pushups": g.pushups,
                "status": g.status,
            }
            for g in games
        ],
    }


@app.options("/{path:path}")
def options_handler(path: str):
    return {}


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def extract_game_id(pgn: str):
    for line in pgn.splitlines():
        if line.startswith("[Site "):
            site = line.split('"')[1]
            if "/" in site:
                return site.split("/")[-1]
    return None


def extract_played_at(pgn: str):
    date, time = None, None

    for line in pgn.splitlines():
        if line.startswith("[UTCDate "):
            date = line.split('"')[1]
        elif line.startswith("[UTCTime "):
            time = line.split('"')[1]

    if not date or not time:
        return datetime.now(timezone.utc)

    try:
        return datetime.strptime(
            f"{date} {time}", "%Y.%m.%d %H:%M:%S"
        ).replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def normalize_pgn(pgn: str) -> str:
    pgn = pgn.strip().replace("\ufeff", "")

    if not pgn.startswith("[") and "1." in pgn:
        pgn = f"""
[Event "User Submitted Game"]
[Site "?"]
[Date "????.??.??"]
[Round "?"]
[White "?"]
[Black "?"]
[Result "*"]

{pgn}
"""
    return pgn


def username_from_pgn(pgn: str) -> str:
    """
    Dummy username used internally.
    analyze_pgn only needs this to decide color.
    """
    for line in pgn.splitlines():
        if line.startswith("[White "):
            return line.split('"')[1].strip().lower()
    return "anonymous"
