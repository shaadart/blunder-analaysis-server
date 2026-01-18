from pydantic import BaseModel, Field

class SignupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20)
    lichess_username: str = Field(..., min_length=3, max_length=20)


class UserResponse(BaseModel):
    id: str
    username: str
    lichess_username: str
    joined_at: str


class PGNAnalyzeRequest(BaseModel):
    username: str
    pgn: str
