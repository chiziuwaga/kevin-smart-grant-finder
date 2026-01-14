# Grant Finder - Local Development Setup Guide

Complete guide to setting up the multi-user Grant Finder platform on your local machine.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Setup](#detailed-setup)
4. [External Services Configuration](#external-services-configuration)
5. [Running the Application](#running-the-application)
6. [Testing](#testing)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **PostgreSQL 15+** - [Download](https://www.postgresql.org/download/)
- **Redis 7+** - [Download](https://redis.io/download)
- **Node.js 18+** - [Download](https://nodejs.org/) (for frontend)
- **Git** - [Download](https://git-scm.com/downloads)

### Optional but Recommended

- **PostgreSQL GUI** - pgAdmin, DBeaver, or TablePlus
- **Redis GUI** - RedisInsight
- **API Testing** - Postman or Insomnia
- **Stripe CLI** - For testing webhooks locally

---

## Quick Start

```bash
# 1. Clone repository
git clone https://github.com/your-org/grant-finder.git
cd grant-finder

# 2. Setup environment
cp .env.example .env
# Edit .env with your credentials

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Setup database
createdb grantfinder
alembic upgrade head

# 5. Start services (3 terminals)
# Terminal 1: Redis
redis-server

# Terminal 2: Celery Worker
celery -A celery_app worker --loglevel=info --pool=solo  # Windows
celery -A celery_app worker --loglevel=info  # Mac/Linux

# Terminal 3: FastAPI Server
uvicorn app.main:app --reload

# 6. Start frontend (separate terminal)
cd frontend
npm install
npm start

# Access: http://localhost:8000 (API), http://localhost:3000 (Frontend)
```

---

## Detailed Setup

### 1. Clone and Navigate

```bash
git clone https://github.com/your-org/grant-finder.git
cd grant-finder
```

### 2. Python Environment Setup

#### Option A: Using venv (Recommended)
```bash
python -m venv venv

# Activate
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Option B: Using conda
```bash
conda create -n grantfinder python=3.11
conda activate grantfinder
pip install -r requirements.txt
```

### 3. PostgreSQL Setup

#### macOS (Homebrew)
```bash
brew install postgresql@15
brew services start postgresql@15

# Create database
createdb grantfinder

# Create user (optional)
psql postgres
CREATE USER grantfinder WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE grantfinder TO grantfinder;
\q
```

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database
sudo -u postgres createdb grantfinder
sudo -u postgres psql
CREATE USER grantfinder WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE grantfinder TO grantfinder;
\q
```

#### Windows
1. Download installer from [postgresql.org](https://www.postgresql.org/download/windows/)
2. Run installer (remember the password!)
3. Open pgAdmin
4. Create database "grantfinder"

### 4. Redis Setup

#### macOS (Homebrew)
```bash
brew install redis
brew services start redis

# Test
redis-cli ping  # Should return "PONG"
```

#### Ubuntu/Debian
```bash
sudo apt-get install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# Test
redis-cli ping  # Should return "PONG"
```

#### Windows (Docker - Easiest)
```bash
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

#### Windows (Native)
Download from [redis.io](https://redis.io/download) or use WSL2.

### 5. Environment Configuration

```bash
# Copy example
cp .env.example .env

# Edit .env with your text editor
nano .env  # or code .env, vim .env, etc.
```

**Minimum Required Variables:**
```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres  # or grantfinder
DB_PASSWORD=your_password
DB_NAME=grantfinder

# Redis
REDIS_URL=redis://localhost:6379/0

# Auth0 (get from auth0.com)
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_API_AUDIENCE=https://api.grantfinder.com

# Stripe (get from dashboard.stripe.com)
STRIPE_SECRET_KEY=sk_test_your_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret
STRIPE_PRICE_ID=price_your_35_dollar_plan

# AI Services
DEEPSEEK_API_KEY=sk-your-key
AGENTQL_API_KEY=your-key
PINECONE_API_KEY=your-key

# Email
RESEND_API_KEY=re_your_key
```

### 6. Database Migrations

```bash
# Initialize Alembic (if not already done)
alembic init migrations

# Run migrations
alembic upgrade head

# Check status
alembic current

# If you need to create a new migration
alembic revision --autogenerate -m "Description"
```

### 7. Frontend Setup

```bash
cd frontend
npm install

# Create frontend .env
cat > .env.local << EOF
REACT_APP_API_URL=http://localhost:8000
REACT_APP_AUTH0_DOMAIN=your-tenant.us.auth0.com
REACT_APP_AUTH0_CLIENT_ID=your_client_id
REACT_APP_STRIPE_PUBLISHABLE_KEY=pk_test_your_key
EOF

# Start development server
npm start
```

---

## External Services Configuration

### Auth0 Setup

1. **Create Account**: [https://auth0.com](https://auth0.com)

2. **Create Tenant**:
   - Choose region (US, EU, etc.)
   - Name: "grant-finder-dev"

3. **Create API**:
   - Name: "Grant Finder API"
   - Identifier: `https://api.grantfinder.com`
   - Signing Algorithm: RS256
   - Enable RBAC
   - Add Permissions in Access Token: ✅

4. **Create Application** (Single Page Application):
   - Name: "Grant Finder Frontend"
   - Type: Single Page Application
   - Copy Client ID and Domain

5. **Configure URLs**:
   - Allowed Callback URLs: `http://localhost:3000/callback`
   - Allowed Logout URLs: `http://localhost:3000`
   - Allowed Web Origins: `http://localhost:3000`
   - Allowed Origins (CORS): `http://localhost:3000`

6. **Update .env**:
   ```bash
   AUTH0_DOMAIN=your-tenant.us.auth0.com
   AUTH0_API_AUDIENCE=https://api.grantfinder.com
   ```

### Stripe Setup

1. **Create Account**: [https://dashboard.stripe.com](https://dashboard.stripe.com)

2. **Toggle to Test Mode** (top right)

3. **Get API Keys**: Developers > API keys
   - Publishable key: `pk_test_...`
   - Secret key: `sk_test_...`

4. **Create Product**:
   - Products > Add Product
   - Name: "Grant Finder Basic"
   - Description: "50 searches + 20 applications per month"
   - Pricing: $35.00 USD / month
   - Copy Price ID: `price_...`

5. **Setup Webhook** (Local Development):
   ```bash
   # Install Stripe CLI
   brew install stripe/stripe-cli/stripe  # Mac
   # Or download from https://stripe.com/docs/stripe-cli

   # Login
   stripe login

   # Forward webhooks to local server
   stripe listen --forward-to localhost:8000/api/webhooks/stripe

   # Copy webhook secret (whsec_...)
   ```

6. **Update .env**:
   ```bash
   STRIPE_SECRET_KEY=sk_test_your_key
   STRIPE_PUBLISHABLE_KEY=pk_test_your_key
   STRIPE_WEBHOOK_SECRET=whsec_your_secret_from_cli
   STRIPE_PRICE_ID=price_your_product_id
   ```

### DeepSeek AI Setup

1. **Create Account**: [https://platform.deepseek.com](https://platform.deepseek.com)
2. **Generate API Key**: Dashboard > API Keys
3. **Add Billing**: Add payment method (pay-as-you-go)
4. **Update .env**:
   ```bash
   DEEPSEEK_API_KEY=sk-your-key-here
   ```

### AgentQL Setup

1. **Create Account**: [https://agentql.com](https://agentql.com)
2. **Generate API Key**: Dashboard > API Keys
3. **Update .env**:
   ```bash
   AGENTQL_API_KEY=your-key-here
   ```

### Pinecone Setup

1. **Create Account**: [https://www.pinecone.io](https://www.pinecone.io)
2. **Create Index**:
   - Name: `grantcluster`
   - Dimensions: `1536` (for DeepSeek embeddings)
   - Metric: `cosine`
   - Region: `us-east-1` (or nearest)
3. **Copy API Key**: Dashboard > API Keys
4. **Update .env**:
   ```bash
   PINECONE_API_KEY=your-key-here
   PINECONE_INDEX_NAME=grantcluster
   ```

### Resend Setup

1. **Create Account**: [https://resend.com](https://resend.com)
2. **Add Domain** (optional for dev, use `onboarding@resend.dev`)
3. **Generate API Key**: API Keys > Create
4. **Update .env**:
   ```bash
   RESEND_API_KEY=re_your_key_here
   FROM_EMAIL=onboarding@resend.dev  # or your domain
   ```

---

## Running the Application

### Start All Services

You need **4 terminal windows**:

#### Terminal 1: Redis
```bash
redis-server
# Should show "Ready to accept connections"
```

#### Terminal 2: Celery Worker
```bash
# Windows
celery -A celery_app worker --loglevel=info --pool=solo

# Mac/Linux
celery -A celery_app worker --loglevel=info

# Should show "celery@hostname ready"
```

#### Terminal 3: Celery Beat (Optional - for scheduled tasks)
```bash
celery -A celery_app beat --loglevel=info
# Should show "Scheduler: Sending due task..."
```

#### Terminal 4: FastAPI Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Should show "Application startup complete"
```

#### Terminal 5: Frontend (React)
```bash
cd frontend
npm start
# Should open http://localhost:3000
```

### Access Points

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs (Swagger)**: http://localhost:8000/api/docs
- **API Docs (ReDoc)**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health

---

## Testing

### Run Backend Tests
```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov=services --cov=tasks

# Specific test file
pytest tests/test_auth.py

# Verbose output
pytest -v -s
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8000/health

# Get dashboard stats (requires auth token)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/dashboard/stats

# Create grant search
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"query": "technology grants"}'
```

### Test Celery Tasks
```python
# Python shell
python

from tasks.application_generator import generate_grant_application
result = generate_grant_application.delay(user_id=1, grant_id=123, business_profile_id=1)
print(result.id)  # Task ID

# Check result (blocking)
print(result.get(timeout=600))
```

---

## Troubleshooting

### Database Connection Issues

**Error**: `could not connect to server`
```bash
# Check PostgreSQL is running
pg_isready

# Check port
lsof -i :5432  # Mac/Linux
netstat -ano | findstr :5432  # Windows

# Restart PostgreSQL
brew services restart postgresql@15  # Mac
sudo systemctl restart postgresql  # Linux
```

### Redis Connection Issues

**Error**: `Connection refused`
```bash
# Check Redis is running
redis-cli ping  # Should return "PONG"

# Check port
lsof -i :6379  # Mac/Linux
netstat -ano | findstr :6379  # Windows

# Restart Redis
brew services restart redis  # Mac
sudo systemctl restart redis  # Linux
docker restart redis  # Docker
```

### Celery Not Starting

**Error**: `Task handler raised error: ValueError`
```bash
# Windows MUST use --pool=solo
celery -A celery_app worker --loglevel=info --pool=solo

# Check Redis connection
redis-cli ping

# Check CELERY_BROKER_URL in .env
echo $CELERY_BROKER_URL  # Should be redis://localhost:6379/0
```

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'X'`
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Check virtual environment is activated
which python  # Should show venv path

# Rebuild environment
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Migration Errors

**Error**: `Target database is not up to date`
```bash
# Check current version
alembic current

# See history
alembic history

# Downgrade if needed
alembic downgrade -1

# Upgrade to latest
alembic upgrade head

# Force stamp (if out of sync)
alembic stamp head
```

### Auth0 Token Invalid

**Error**: `401 Unauthorized`
- Check AUTH0_DOMAIN matches your tenant
- Verify AUTH0_API_AUDIENCE is correct
- Ensure token hasn't expired (default 24 hours)
- Check token format: `Bearer <token>`

### Stripe Webhook Fails

**Error**: `Webhook signature verification failed`
```bash
# Ensure Stripe CLI is running
stripe listen --forward-to localhost:8000/api/webhooks/stripe

# Copy the webhook secret (whsec_...) to .env
STRIPE_WEBHOOK_SECRET=whsec_your_secret_here

# Restart FastAPI server
```

### Frontend Won't Start

**Error**: `npm ERR!`
```bash
# Clear cache
rm -rf node_modules package-lock.json
npm cache clean --force
npm install

# Check Node version
node --version  # Should be 18+

# Try different port
PORT=3001 npm start
```

---

## Development Workflow

### Daily Workflow
```bash
# 1. Pull latest changes
git pull origin main

# 2. Update dependencies (if changed)
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 3. Run migrations (if new)
alembic upgrade head

# 4. Start services (4 terminals)
redis-server
celery -A celery_app worker --loglevel=info --pool=solo
uvicorn app.main:app --reload
cd frontend && npm start

# 5. Make changes, test, commit
git add .
git commit -m "Your changes"
git push
```

### Create New Migration
```bash
# After changing models in database/models.py
alembic revision --autogenerate -m "Add new field to User"

# Review the migration file in migrations/versions/
# Edit if needed

# Apply migration
alembic upgrade head
```

### Add New Celery Task
1. Create task in `tasks/your_task.py`
2. Import in `celery_app.py`
3. Restart Celery worker
4. Test: `your_task.delay(args)`

---

## Next Steps

- **Read the API Docs**: http://localhost:8000/api/docs
- **Check the Code**: Explore `app/`, `services/`, `tasks/`
- **Run Tests**: `pytest`
- **Deploy to Render**: See `render.yaml`

---

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/your-org/grant-finder/issues)
- **Docs**: [Full Documentation](https://docs.grantfinder.com)
- **Email**: support@grantfinder.com

---

**Happy Coding! 🚀**
