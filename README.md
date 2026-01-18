# ♟️ PushupChess Backend API

FastAPI-based server for chess game analysis, user management, and pushup calculations.

## 🎯 Features

- **Game Analysis** - Analyze chess games using Stockfish engine
- **Lichess Integration** - Fetch and analyze games from Lichess
- **User Management** - Track users and their chess statistics
- **Pushup Calculation** - Calculate pushups earned from game performance
- **REST API** - Well-documented API with Swagger UI
- **PostgreSQL Database** - Persistent storage with SQLAlchemy ORM

## 🛠️ Requirements

- Python 3.10+
- PostgreSQL 12+
- Stockfish chess engine
- pip (Python package manager)

## 📦 Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/chesspushup.git
cd chesspushup/stockfish-server
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate it
source .venv/bin/activate    # macOS/Linux
.venv\Scripts\activate       # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy `.env.example` to `.env` and update with your settings:

```bash
cp .env.example .env
```

Edit `.env`:
```env
DATABASE_URL=postgresql://username:password@localhost:5432/pushupchess
```

### 5. Initialize Database

```bash
python app/init_db.py
```

### 6. Run Server

```bash
# Development (with auto-reload)
python -m uvicorn app.main:app --reload

# Production
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Visit `http://localhost:8000/docs` for interactive API documentation.

## 🔌 API Endpoints

### User Management

```
POST   /signup              - Create new user
GET    /users/{user_id}    - Get user details
GET    /users/username/{username} - Get user by username
```

### Game Analysis

```
POST   /analyze-latest-game        - Analyze latest Lichess game
GET    /games/{game_id}           - Get game details
GET    /users/{user_id}/games     - Get user's games
```

### Lichess Integration

```
POST   /fetch-games               - Fetch games from Lichess
GET    /suggest-usernames         - Suggest Lichess usernames
```

### Statistics & Pushups

```
GET    /users/{user_id}/pushups-due      - Pushups owed
GET    /users/{user_id}/pushups-forgiven - Forgiven pushups
GET    /users/{user_id}/stats            - User statistics
```

See full API documentation at `/docs` when server is running.

## 📁 Project Structure

```
app/
├── main.py                 # FastAPI application
├── db.py                   # Database setup
├── models.py               # SQLAlchemy models
├── schemas.py              # Pydantic request/response schemas
├── crud.py                 # Database operations
├── pgn_analysis.py         # Chess analysis logic
├── bootstrap.py            # Bootstrap analysis
├── fetch_lichess_games.py  # Lichess API integration
├── utils.py                # Utility functions
└── api_services.py         # External API clients

requirements.txt            # Python dependencies
.env.example               # Environment template
Dockerfile                 # Docker configuration
```

## 🗄️ Database Models

### User
```python
{
  "id": UUID,
  "username": str,
  "lichess_username": str,
  "total_pushups": int,
  "forgiven_pushups": int,
  "created_at": datetime,
  "updated_at": datetime
}
```

### Game
```python
{
  "id": UUID,
  "user_id": UUID,
  "lichess_game_id": str,
  "pgn": str,
  "result": "win|loss|draw",
  "pushups_earned": int,
  "analyzed_at": datetime,
  "created_at": datetime
}
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_crud.py

# Run specific test function
pytest tests/test_crud.py::test_create_user
```

## 📝 Configuration

### Database

By default, SQLAlchemy uses PostgreSQL. To use a different database, update the `DATABASE_URL` in `.env`:

```env
# PostgreSQL (default)
DATABASE_URL=postgresql://user:password@localhost/pushupchess

# SQLite (development)
DATABASE_URL=sqlite:///./test.db
```

### Stockfish Engine

Install Stockfish on your system:

```bash
# macOS
brew install stockfish

# Ubuntu/Debian
apt-get install stockfish

# Windows
# Download from https://stockfishchess.org/download/
```

### CORS Configuration

Edit `app/main.py` to restrict CORS in production:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🐳 Docker

```bash
# Build Docker image
docker build -t pushupchess-api .

# Run with Docker
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:password@host:5432/db \
  pushupchess-api
```

## 🔐 Security Considerations

1. **Never commit `.env` files** - They're in `.gitignore`
2. **Use strong database passwords** - For production
3. **Enable HTTPS** - In production deployments
4. **Rate limiting** - Consider adding rate limits for public endpoints
5. **Input validation** - All inputs are validated via Pydantic schemas
6. **CORS restrictions** - Restrict to known domains in production

## 📊 Performance Tips

- **Database indexing** - Ensure common query fields are indexed
- **Connection pooling** - SQLAlchemy manages this automatically
- **API caching** - Consider caching Lichess API responses
- **Async processing** - Use `BackgroundTasks` for heavy operations

## 🚨 Troubleshooting

### "ModuleNotFoundError: No module named 'sqlalchemy'"
```bash
pip install -r requirements.txt
```

### "psycopg2 error: could not translate host name"
- Ensure PostgreSQL is running
- Check `DATABASE_URL` is correct
- Try: `psql postgresql://user:password@localhost/pushupchess`

### "Stockfish not found"
```bash
# Install Stockfish
brew install stockfish  # macOS
apt-get install stockfish  # Linux

# Verify installation
which stockfish
```

### "Address already in use" (port 8000)
```bash
# Use different port
python -m uvicorn app.main:app --port 8001
```

## 🤝 Contributing

See [../CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.

## 📄 License

This project is licensed under the MIT License - see [../LICENSE](../LICENSE) for details.

## 🔗 Related

- **Mobile App**: See [../pushupchess/README.md](../pushupchess/README.md)
- **Data Scripts**: See [../README.md](../README.md)
- **Main Project**: See [../README.md](../README.md)

## 📚 Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org)
- [Python-Chess Documentation](https://python-chess.readthedocs.io)
- [Stockfish Documentation](https://stockfishchess.org)
- [Lichess API Documentation](https://lichess.org/api)

---

Built with ♟️ and FastAPI 🚀
