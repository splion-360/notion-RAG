# Notion Search System

A Python-based system that indexes Notion pages and provides vector-powered search using Paragon API integration and Supabase with pgVector.

## Features

- Authenticate users via Paragon API
- Index Notion pages from the past 6 months
- Store embeddings in Supabase with pgVector
- Fast semantic search using vector similarity
- RESTful API for indexing and search operations

## Prerequisites

- Python 3.10 or higher
- Docker (for local Supabase)
- Supabase CLI (`brew install supabase/tap/supabase` or see [docs](https://supabase.com/docs/guides/cli))
- Paragon API credentials
- OpenAI API key (optional, or use local sentence-transformers)

## Installation

### 1. Clone the repository
```bash
cd /home/splion/Desktop/personal/interviews/constella
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up Supabase (Local Development)

**Start local Supabase:**
```bash
supabase start
```

This will:
- Start PostgreSQL, PostgREST, Storage, and other services
- Output your local credentials (save these!)
- Local Studio UI: http://localhost:54323

**Run migrations:**
```bash
supabase db push
```

This applies all migrations in `supabase/migrations/`

**Get your connection details:**
```bash
supabase status
```

Note the `API URL` and `anon key` for your `.env` file.

### 5. Set up environment variables
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```bash
# From supabase status
SUPABASE_URL=http://localhost:54321
SUPABASE_KEY=your_anon_key_here

# Paragon credentials
PARAGON_API_KEY=your_paragon_key
PARAGON_PROJECT_ID=your_project_id

# Choose embedding model
EMBEDDING_MODEL=sentence-transformers  # or "openai"
```

## Configuration

Edit the `.env` file with your credentials:

- `PARAGON_API_KEY`: Your Paragon API key
- `PARAGON_PROJECT_ID`: Your Paragon project ID
- `SUPABASE_URL`: Your Supabase instance URL
- `SUPABASE_KEY`: Your Supabase service role key
- `OPENAI_API_KEY`: Your OpenAI API key (if using OpenAI embeddings)
- `EMBEDDING_MODEL`: Choose `openai` or `sentence-transformers`

## Usage

### Start the API server:

**Option 1: Using the main entry point**
```bash
python main.py
```

**Option 2: Using uvicorn directly**
```bash
uvicorn app.api.main:app --reload
```

The API will be available at `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Alternative Docs: `http://localhost:8000/redoc`

### API Endpoints

#### Authentication
**Get Paragon Connect URL:**
```bash
POST /auth/connect
{
  "paragon_user_id": "user@example.com"
}
```

**Verify Notion Connection:**
```bash
POST /auth/verify
{
  "paragon_user_id": "user@example.com"
}
```

**Store Access Token:**
```bash
POST /auth/store-token
{
  "paragon_user_id": "user@example.com",
  "access_token": "token_from_paragon"
}
```

## Project Structure

```
.
├── app/
│   ├── api/           # FastAPI application
│   │   └── main.py    # Main app, middleware, exception handlers
│   ├── routers/       # API route handlers
│   │   ├── auth.py    # Authentication endpoints
│   │   └── health.py  # Health check endpoints
│   ├── services/      # Business logic services
│   │   └── paragon.py # Paragon API client
│   ├── database/      # Database layer
│   │   ├── connection.py  # Supabase client
│   │   └── operations.py  # Database operations
│   ├── models/        # Pydantic models
│   │   ├── base.py    # Common models
│   │   ├── search.py  # Search models (future)
│   │   ├── indexing.py # Indexing models (future)
│   │   └── users.py   # User models
│   └── utils/         # Utility functions
├── config/            # Configuration & settings
│   ├── settings.py    # Pydantic settings
│   └── logger.py      # Custom logger
├── supabase/          # Supabase migrations
├── tests/             # Test suite
├── main.py            # Application entry point
├── requirements.txt   # Python dependencies
├── pyproject.toml     # Project configuration
└── README.md          # This file
```

## Development

Run tests:
```bash
pytest
```

Format code:
```bash
black .
ruff check .
```

Type checking:
```bash
mypy src/
```

## License

MIT
