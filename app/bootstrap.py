from datetime import datetime
from sqlalchemy.orm import Session
from .db import SessionLocal
from .utils import fetch_recent_pgns
from .pgn_analysis import analyze_pgn
from .crud import create_game, get_game_by_id
from .models import User

BOOTSTRAP_GAMES = 5


def bootstrap_analysis(user_id: str):
    """Runs in background — fetch and analyze last N Lichess games"""
    db: Session = SessionLocal()

    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print("Bootstrap failed: user not found")
            return

        games = fetch_recent_pgns(user.lichess_username, BOOTSTRAP_GAMES)

        for game_json in games:
      
            if get_game_by_id(db, game_json["id"]):
                continue

            result = analyze_pgn(
                pgn=game_json["pgn"],
                username=user.lichess_username
            )

            create_game(
                db=db,
                game_id=game_json["id"],
                user_id=user.id,
                played_at=datetime.fromtimestamp(game_json["createdAt"] / 1000),
                mode=result["game_mode"],
                player_color=result["player_color"],
                opponent=result["opponent"],
                blunders=result["blunders"],
                pushups=result["pushups"],
                status="forgiven"
            )

        db.commit()
        print(f"🔥 Bootstrap complete for {user.username}")

    except Exception as e:
        print(f"⚠️ Bootstrap crashed: {e}")

    finally:
        db.close()
