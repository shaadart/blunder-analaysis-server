import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func
from .models import User, Game

def username_exists(db: Session, username: str) -> bool:
    return db.query(User).filter(User.username == username).first() is not None


def suggest_usernames(db: Session, base_username: str, limit: int = 3):
    suggestions = []
    i = 2

    while len(suggestions) < limit:
        candidate = f"{base_username}_{i}"
        if not username_exists(db, candidate):
            suggestions.append(candidate)
        i += 1

    return suggestions


def create_user(db: Session, username: str, lichess_username: str):
    user = User(
        id=uuid.uuid4(),
        username=username.lower(),
        lichess_username=lichess_username.lower()
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def create_game(
    db,
    *,
    game_id,
    user_id,
    played_at,
    mode,
    player_color,
    opponent,
    blunders,
    pushups,
    status
):
    game = Game(
        id=game_id,
        user_id=user_id,
        played_at=played_at,
        mode=mode,
        player_color=player_color,
        opponent=opponent,
        blunders=blunders,
        pushups=pushups,
        status=status
    )
    db.add(game)
    db.commit()

def get_pushups_due(db, user_id):
    return db.query(func.coalesce(func.sum(Game.pushups), 0)) \
        .filter(Game.user_id == user_id, Game.status == "new") \
        .scalar()

def get_pushups_forgiven(db, user_id):
    return db.query(func.coalesce(func.sum(Game.pushups), 0)) \
        .filter(Game.user_id == user_id, Game.status == "forgiven") \
        .scalar()

def get_recent_games(db, user_id, limit=5):
    return db.query(Game) \
        .filter(Game.user_id == user_id) \
        .order_by(Game.played_at.desc()) \
        .limit(limit) \
        .all()

def get_game_by_id(db: Session, game_id: str):
    return db.query(Game).filter(Game.id == game_id).first()
