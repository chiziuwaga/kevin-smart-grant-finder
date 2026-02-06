# Smart Grant Finder

AI-powered grant discovery and application generation platform for nonprofits, small businesses, and community organizations.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI (Python 3.12), SQLAlchemy 2.0, Alembic |
| **Frontend** | React 18, TypeScript, Swiss UI design system |
| **Database** | PostgreSQL with pgvector for embeddings |
| **AI Engine** | DeepSeek (reasoning + embeddings) |
| **Web Scraping** | AgentQL + Playwright |
| **Background Jobs** | Celery + Redis |
| **Email** | Resend API |
| **Auth** | Email/password JWT (HS256, bcrypt) |
| **Deployment** | Render (unified service: API + static frontend) |

## Features

### Grant Discovery
- **DeepSeek Reasoning Search** - Chunked recursive queries across federal, state, and foundation databases
- **Multi-dimensional Scoring** - Relevance, compliance, feasibility, and strategic alignment
- **Automated Monitoring** - Celery Beat runs searches every 6 hours for active users
- **Deduplication** - By URL and title, within and across search runs

### Application Generation
- **RAG-powered** - Uses business profile narrative + grant details to generate tailored applications
- **Structured Sections** - Executive summary, needs statement, project description, budget narrative
- **Edit & Submit** - Review, edit, and track application status

### User Experience
- **Business Profile** - Target sectors, geographic focus, revenue range, narrative text
- **Dashboard** - Grants grid with filters, scores, deadlines, bulk actions
- **Saved Grants** - Bookmark and track interesting opportunities
- **Email Notifications** - Post-search summaries, grant alerts, usage warnings, weekly reports
- **Swiss Design** - Clean, professional UI with Inter font and minimal color palette

## Local Development

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL 14+ with pgvector extension
- Redis

### Setup

```bash
# Clone
git clone https://github.com/your-org/kevin-smart-grant-finder.git
cd kevin-smart-grant-finder

# Backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..

# Environment
cp .env.example .env
# Edit .env with your keys (DEEPSEEK_API_KEY, RESEND_API_KEY, DATABASE_URL, etc.)

# Database
alembic upgrade head

# Run
uvicorn app.main:app --reload --port 8000
# In another terminal:
cd frontend && npm start
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |
| `SECRET_KEY` | JWT signing secret |
| `DEEPSEEK_API_KEY` | DeepSeek API key |
| `RESEND_API_KEY` | Resend email API key |
| `FROM_EMAIL` | Sender email address |
| `FRONTEND_URL` | Frontend URL for email links |

## Deployment (Render)

The app deploys as a single unified service:
- FastAPI serves the API at `/api/*`
- React static build served at `/`
- Dockerfile handles both Python + Node builds

### Steps
1. Create a PostgreSQL database on Render
2. Create a Redis instance on Render (manual, not in render.yaml)
3. Create a Web Service pointing to this repo
4. Set environment variables in Render dashboard
5. Deploy - `render.yaml` handles pre-deploy migrations

### Architecture

```
                    Render Web Service
                    ┌─────────────────────┐
  Browser ─────────>│  FastAPI (uvicorn)   │
                    │  /api/* -> API routes│
                    │  /*     -> React SPA │
                    └────────┬────────────┘
                             │
              ┌──────────────┼──────────────┐
              v              v              v
         PostgreSQL       Redis         DeepSeek
         (data +        (Celery        (AI reasoning
          pgvector)      broker)        + embeddings)
```

## Scheduled Tasks (Celery Beat)

| Task | Schedule | Purpose |
|------|----------|---------|
| Grant searches | Every 6 hours | Discover new grants for all active users |
| Usage warnings | Daily 9 AM UTC | Warn users approaching monthly limits |
| Weekly reports | Monday 10 AM UTC | Summarize weekly grant activity |
| Monthly reset | 1st of month | Reset search/application counters |
| Embedding cleanup | Sunday 2 AM UTC | Remove stale vector data |
| Grant archival | Sunday 3 AM UTC | Archive past-deadline grants |

## API Endpoints

### Auth
- `POST /api/auth/register` - Create account
- `POST /api/auth/login` - Get JWT tokens
- `POST /api/auth/refresh` - Refresh access token
- `GET /api/auth/me` - Current user profile

### Grants
- `GET /api/grants` - List grants (paginated, filterable)
- `POST /api/grants/search` - Search with filters
- `GET /api/grants/{id}` - Grant details
- `POST /api/grants/{id}/save` - Save grant
- `DELETE /api/grants/{id}/save` - Unsave grant

### Business Profile
- `GET /api/business-profile` - Get profile
- `PUT /api/business-profile` - Update profile

### Applications
- `GET /api/applications` - List generated applications
- `POST /api/applications/generate` - Generate application for grant

### System
- `GET /api/health` - Health check
- `POST /api/system/run-search` - Trigger manual search
- `GET /api/search-runs` - Search run history

## License

Private - All rights reserved.
