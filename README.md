# Notion RAG

A full-stack application for indexing and searching Notion pages using vector embeddings and semantic search.

## Tech Stack

**Backend**: Python, FastAPI, Supabase, pgVector
**Frontend**: React, TypeScript, Vite, Material UI
**Integration**: Pipedream Connect API

## Features

- User authentication with email/password
- Notion workspace integration via Pipedream
- Vector-based semantic search
- Light/dark theme support

## Setup

### Backend

1. Activate virtual environment:
```bash
source .venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start local Supabase:
```bash
supabase start
```

4. Run migrations:
```bash
supabase db reset
```

5. Start API server:
```bash
python main.py
```

API available at http://localhost:8000

### Frontend

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Configure environment variables in `.env`

3. Start dev server:
```bash
npm run dev
```

Frontend available at http://localhost:3000

## Environment Variables

Copy `.env.example` to `.env` and configure:
- Supabase credentials
- Pipedream credentials
- Embedding model settings