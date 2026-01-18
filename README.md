# Blunder Analysis API

## Overview

A production-grade FastAPI server engineered for computational chess analysis, integrating Stockfish evaluation with human cognitive modeling to quantify positional mistakes and translate them into physical accountability metrics.

This system bridges the gap between algorithmic precision and practical decision-making, implementing context-aware classification that distinguishes genuine tactical oversights from acceptable strategic simplifications.


<img width="1866" height="977" alt="image" src="https://github.com/user-attachments/assets/bb783b2e-e7f7-4b84-b895-160e53b73ef8" />


---

## Table of Contents

- [Core Features](#core-features)
- [System Architecture](#system-architecture)
- [Technical Requirements](#technical-requirements)
- [Installation Guide](#installation-guide)
- [API Reference](#api-reference)
- [Analysis Engine](#analysis-engine)
- [Database Schema](#database-schema)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Security](#security)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)

---

## Core Features

**Intelligent Game Analysis**
- Multi-dimensional move evaluation using Stockfish 16
- Context-aware blunder classification with game-phase sensitivity
- Tactical punishment detection for hanging pieces and mate threats
- Win probability regression analysis with centipawn conversion

**Lichess Integration**
- Automated game fetching via Lichess public API
- PGN parsing with metadata extraction
- Username suggestion and validation
- Real-time game synchronization

**User Management System**
- UUID-based user identification
- Persistent storage of analysis history
- Pushup debt tracking with forgiveness mechanisms
- Statistical aggregation across multiple games

**RESTful API Architecture**
- OpenAPI 3.0 specification with Swagger UI documentation
- Pydantic schema validation for type safety
- PostgreSQL persistence with SQLAlchemy ORM
- CORS-enabled for cross-origin client integration

---

## System Architecture

```
┌─────────────┐
│   Client    │
│ Application │
└──────┬──────┘
       │ HTTP/REST
       ▼
┌─────────────────────────────────┐
│      FastAPI Application        │
│  ┌───────────────────────────┐  │
│  │   API Layer (main.py)     │  │
│  └───────────┬───────────────┘  │
│              │                   │
│  ┌───────────▼───────────────┐  │
│  │  Business Logic Layer     │  │
│  │  - pgn_analysis.py        │  │
│  │  - bootstrap.py           │  │
│  │  - fetch_lichess_games.py │  │
│  └───────────┬───────────────┘  │
│              │                   │
│  ┌───────────▼───────────────┐  │
│  │   Data Access Layer       │  │
│  │  - crud.py                │  │
│  │  - models.py              │  │
│  └───────────┬───────────────┘  │
└──────────────┼───────────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
    ▼          ▼          ▼
┌─────────┐ ┌──────┐ ┌──────────┐
│Stockfish│ │ DB   │ │ Lichess  │
│ Engine  │ │(SQL) │ │   API    │
└─────────┘ └──────┘ └──────────┘
```

---

## Technical Requirements

**Runtime Environment**
- Python 3.10 or higher
- PostgreSQL 12+ (production) or SQLite 3+ (development)
- Stockfish chess engine (any recent version)

**Python Dependencies**
- FastAPI framework for API layer
- SQLAlchemy for database ORM
- Pydantic for data validation
- python-chess for game parsing and board representation
- stockfish for engine integration
- uvicorn for ASGI server

**System Dependencies**
- pip package manager
- PostgreSQL client libraries (psycopg2)
- Git for version control

---

## Installation Guide

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/chesspushup.git
cd chesspushup/stockfish-server
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate    # macOS/Linux
.venv\Scripts\activate       # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment

Copy `.env.example` to `.env` and update with your settings:

```bash
cp .env.example .env
```

Edit `.env`:
```env
DATABASE_URL=postgresql://username:password@localhost:5432/pushupchess
```

### Step 5: Initialize Database

```bash
python app/init_db.py
```

### Step 6: Run Server

```bash
# Development (with auto-reload)
python -m uvicorn app.main:app --reload

# Production
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000/docs` for interactive API documentation.

---

## API Reference

### User Management

```
POST   /signup                      Create new user account
GET    /users/{user_id}             Retrieve user details
GET    /users/username/{username}   Query user by username
```

### Game Analysis

```
POST   /analyze-latest-game         Analyze most recent Lichess game
GET    /games/{game_id}             Retrieve game analysis details
GET    /users/{user_id}/games       List all games for user
```

### Lichess Integration

```
POST   /fetch-games                 Fetch games from Lichess API
GET    /suggest-usernames           Suggest Lichess usernames
```

### Statistics & Pushups

```
GET    /users/{user_id}/pushups-due       Total pushups owed
GET    /users/{user_id}/pushups-forgiven  Forgiven pushup count
GET    /users/{user_id}/stats             User performance statistics
```

Complete API documentation available at `/docs` endpoint when server is running.

---

## Analysis Engine

### Core Philosophy

The analysis engine implements a human-centric evaluation model that distinguishes between genuine blunders and acceptable positional compromises. Unlike pure engine analysis, this system considers:

- **Game Phase Context**: Opening moves receive lenient evaluation due to theoretical flexibility
- **Tactical Obviousness**: Hanging pieces and forced material loss are weighted heavily
- **Win Probability Regression**: Evaluations converted to winning percentage changes
- **Strategic Intent Recognition**: Position simplification distinguished from calculation errors

### Classification Methodology

**Blunder Detection Criteria**

A move is classified as a blunder when it satisfies any of the following conditions:

1. **Regret Threshold**: Win probability loss exceeds 20%
2. **Evaluation Swing**: Centipawn loss greater than 400
3. **Position Reversal**: Conversion from winning (+2.0) to losing (-1.0) position
4. **Tactical Punishment**: Move allows immediate material loss or checkmate threat

**Mistake Classification**

Moves classified as mistakes exhibit:
- Regret between 8-20% in middlegame positions
- Clear suboptimal play without catastrophic consequences
- Recoverable positional disadvantage

**Inaccuracy Recognition**

Minor positional compromises characterized by:
- Regret between 2-8%
- Suboptimal but understandable decisions
- Minimal practical impact on game outcome

### Pushup Calculation Algorithm

```python
pushups = blunders × 10
```

Only moves classified as blunders contribute to pushup debt. Mistakes and inaccuracies serve as educational feedback without physical consequences.

### Technical Implementation

**Stockfish Integration**
- Analysis depth: 18 plies
- Position evaluation caching for performance optimization
- Best move extraction for comparative analysis

**Win Probability Conversion**
- Centipawn evaluation normalized to percentage values
- Lichess regression model for probability calculation
- Mate detection with infinity value assignment

---

## Database Schema

### User Model

```python
class User(Base):
    id: UUID                    # Primary key
    username: str               # Display name
    lichess_username: str       # Lichess account identifier
    total_pushups: int          # Cumulative pushup debt
    forgiven_pushups: int       # Pardoned pushup count
    created_at: datetime        # Account creation timestamp
    updated_at: datetime        # Last modification timestamp
```

### Game Model

```python
class Game(Base):
    id: UUID                    # Primary key
    user_id: UUID               # Foreign key to User
    lichess_game_id: str        # Lichess game identifier
    pgn: str                    # Portable Game Notation
    result: str                 # win | loss | draw
    blunders: int               # Count of blunder-level moves
    mistakes: int               # Count of mistake-level moves
    inaccuracies: int           # Count of inaccuracy-level moves
    pushups_earned: int         # Calculated pushup debt
    status: str                 # forgiven | pending
    analyzed_at: datetime       # Analysis completion time
    created_at: datetime        # Record creation timestamp
```

### Entity Relationships

```
User (1) ──────< (N) Game
     │
     └─ Aggregates: total_pushups, forgiven_pushups
```

### Project Structure

```
app/
├── main.py                 # FastAPI application and routing
├── db.py                   # Database connection management
├── models.py               # SQLAlchemy ORM models
├── schemas.py              # Pydantic validation schemas
├── crud.py                 # Database CRUD operations
├── pgn_analysis.py         # Core analysis engine
├── bootstrap.py            # Analysis orchestration
├── fetch_lichess_games.py  # Lichess API client
├── utils.py                # Utility functions
├── analyze.py              # Move evaluation logic
├── dispute_move.py         # Move disputation handling
├── init_db.py              # Database initialization
└── users.py                # User management operations

requirements.txt            # Python dependency specifications
.env.example               # Environment configuration template
Dockerfile                 # Container build instructions
stockfish_16_linux         # Stockfish chess engine binary
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following configuration:

```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/pushupchess

# Stockfish Configuration (optional - defaults to system path)
STOCKFISH_PATH=/usr/local/bin/stockfish

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# CORS Settings (comma-separated origins)
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

### Database Setup

**PostgreSQL (Production)**

```bash
# Create database
createdb pushupchess

# Verify connection
psql postgresql://username:password@localhost:5432/pushupchess
```

**SQLite (Development)**

```env
DATABASE_URL=sqlite:///./development.db
```

SQLite is suitable for local development and testing but not recommended for production deployments.

### Stockfish Configuration

The system requires Stockfish to be installed and accessible. Installation methods vary by platform:

**macOS**
```bash
brew install stockfish
```

**Ubuntu/Debian**
```bash
apt-get install stockfish
```

**Windows**
Download from [stockfishchess.org](https://stockfishchess.org/download/) and add to PATH.

Verify installation:
```bash
which stockfish  # Unix
where stockfish  # Windows
```

---

## Testing

Execute the test suite to verify system integrity:

```bash
# Run all tests
pytest

# Run with coverage reporting
pytest --cov=app --cov-report=html

# Run specific test module
pytest tests/test_crud.py

# Run specific test function
pytest tests/test_crud.py::test_create_user -v

# Run with verbose output
pytest -vv
```

---

## Deployment

### Docker Deployment

Build and run containerized application:

```bash
# Build image
docker build -t pushupchess-api .

# Run container
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  --name pushupchess \
  pushupchess-api

# View logs
docker logs -f pushupchess
```

### Production Considerations

**ASGI Server Configuration**

For production deployments, use Gunicorn with Uvicorn workers:

```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

**Reverse Proxy Setup (Nginx)**

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Process Management (systemd)**

Create `/etc/systemd/system/pushupchess.service`:

```ini
[Unit]
Description=PushupChess API
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/pushupchess
Environment="DATABASE_URL=postgresql://..."
ExecStart=/opt/pushupchess/.venv/bin/gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
systemctl enable pushupchess
systemctl start pushupchess
systemctl status pushupchess
```

---

## Security

### Authentication & Authorization

The current implementation does not include authentication middleware. For production deployments, implement JWT-based authentication:

```python
from fastapi.security import HTTPBearer
from jose import JWTError, jwt

security = HTTPBearer()

@app.get("/protected")
async def protected_route(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Verify JWT token
    token = credentials.credentials
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload
```

### Input Validation

All API inputs are validated through Pydantic schemas, preventing injection attacks and malformed data:

```python
class GameAnalysisRequest(BaseModel):
    pgn: str = Field(..., max_length=50000)
    username: str = Field(..., regex="^[a-zA-Z0-9_-]{3,20}$")
```

### CORS Policy

Restrict CORS origins in production environments. Edit `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.yourdomain.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### Database Security

- Use connection pooling to prevent resource exhaustion
- Employ prepared statements (SQLAlchemy ORM handles this automatically)
- Never expose database credentials in version control
- Implement database-level access controls and encryption at rest
- Regularly rotate credentials and audit access logs

### Rate Limiting

Implement rate limiting for public endpoints to prevent abuse:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/analyze-latest-game")
@limiter.limit("10/minute")
async def analyze_game():
    pass
```

---

## Performance Optimization

### Database Indexing

Critical indexes for query optimization:

```sql
CREATE INDEX idx_games_user_id ON games(user_id);
CREATE INDEX idx_games_created_at ON games(created_at DESC);
CREATE INDEX idx_users_lichess_username ON users(lichess_username);
CREATE INDEX idx_games_lichess_game_id ON games(lichess_game_id);
```

### Caching Strategy

Implement Redis caching for frequently accessed data:

```python
import redis
from functools import lru_cache

redis_client = redis.Redis(host='localhost', port=6379, db=0)

@lru_cache(maxsize=1000)
def get_position_evaluation(fen: str) -> dict:
    # Stockfish evaluation with in-memory caching
    cached = redis_client.get(f"eval:{fen}")
    if cached:
        return json.loads(cached)
    
    result = stockfish.analyze(fen)
    redis_client.setex(f"eval:{fen}", 3600, json.dumps(result))
    return result
```

### Asynchronous Processing

Leverage FastAPI's async capabilities for I/O-bound operations:

```python
@app.post("/analyze-game")
async def analyze_game(background_tasks: BackgroundTasks, game_data: GameRequest):
    background_tasks.add_task(perform_deep_analysis, game_data)
    return {"status": "processing", "message": "Analysis queued"}
```

### Connection Pooling

SQLAlchemy automatically manages connection pooling. Optimize for production:

```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

---

## Troubleshooting

### Dependency Installation Failures

**Error: `ModuleNotFoundError: No module named 'sqlalchemy'`**

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

# Verify installation
pip list | grep sqlalchemy
```

### Database Connection Issues

**Error: `psycopg2 error: could not translate host name`**

Diagnostic steps:
1. Verify PostgreSQL is running: `systemctl status postgresql`
2. Validate `DATABASE_URL` in `.env`
3. Test connection manually: `psql postgresql://user:password@localhost/pushupchess`
4. Check firewall rules and network accessibility

### Stockfish Engine Not Found

**Error: `FileNotFoundError: Stockfish engine not found`**

```bash
# Install Stockfish
brew install stockfish  # macOS
apt-get install stockfish  # Linux/Debian

# Verify installation
which stockfish

# Manually specify path in .env
STOCKFISH_PATH=/usr/local/bin/stockfish
```

### Port Conflicts

**Error: `Address already in use (port 8000)`**

```bash
# Identify process using port
lsof -i :8000  # Unix
netstat -ano | findstr :8000  # Windows

# Use alternative port
python -m uvicorn app.main:app --port 8001

# Or terminate conflicting process
kill -9 <PID>
```

### Analysis Timeout Issues

If Stockfish analysis hangs or times out:

```python
# Adjust analysis depth in pgn_analysis.py
STOCKFISH_DEPTH = 15  # Reduce from 18 for faster analysis

# Implement timeout protection
stockfish.set_skill_level(20)
stockfish.set_depth(15)
```

---

## Contributing

Contributions are welcome. Follow these guidelines:

1. **Fork the repository** and create a feature branch
2. **Write tests** for new functionality
3. **Ensure code passes** linting and type checking
4. **Document changes** in code comments and README
5. **Submit pull request** with clear description of changes

Code style:
- Follow PEP 8 conventions
- Use type hints for function signatures
- Maintain test coverage above 80%

---

## License

This project is licensed under the MIT License. See [LICENSE](../LICENSE) for complete terms.

---

## Resources

**Technical Documentation**
- [FastAPI Documentation](https://fastapi.tiangolo.com) - Web framework reference
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org) - ORM and database toolkit
- [Python-Chess Documentation](https://python-chess.readthedocs.io) - Chess library API
- [Stockfish Documentation](https://stockfishchess.org) - Engine integration guide
- [Lichess API Documentation](https://lichess.org/api) - Game data endpoints

**Research & Theory**
- Multi-Axis Evaluation (MAE) framework for chess analysis
- Human cognitive modeling in decision-making systems
- Win probability calculations and evaluation metrics

---


<img width="1866" height="977" alt="image" src="https://github.com/user-attachments/assets/6796f979-b83b-4125-922a-3e81b8470519" />


---
