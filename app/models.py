from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from .db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    firebase_uid = Column(String, unique=True, nullable=True)
    username = Column(String, unique=True, nullable=False)
    lichess_username = Column(String, nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())


class Game(Base):
    __tablename__ = "games"

    id = Column(String, primary_key=True)  # lichess game id
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    played_at = Column(DateTime(timezone=True))
    mode = Column(String)
    player_color = Column(String)
    opponent = Column(String)
    blunders = Column(Integer)
    pushups = Column(Integer)
    status = Column(String)  # new | done | forgiven


