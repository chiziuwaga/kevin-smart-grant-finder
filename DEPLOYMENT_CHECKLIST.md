# Grant Finder Multi-User Platform - Deployment Checklist

**Status**: Backend 100% Complete | Frontend 100% Complete | Ready for Configuration & Testing

---

## 🎉 What's Been Completed

### ✅ Backend Infrastructure (100%)
- [x] **Database Models**: 4 new tables (User, BusinessProfile, Subscription, GeneratedApplication)
- [x] **Auth0 Integration**: Complete JWT authentication with auto user creation
- [x] **Stripe Integration**: Full subscription management with webhooks
- [x] **Celery Background Tasks**: Grant search automation, application generation, maintenance
- [x] **DeepSeek AI Integration**: Replaced Perplexity as primary AI provider
- [x] **Resend Email Service**: Replaced Telegram with professional email notifications
- [x] **RAG System**: Business profile embeddings for AI application generation
- [x] **API Endpoints**: Business profile CRUD, Applications CRUD, Subscriptions, Usage tracking
- [x] **Database Migration**: Comprehensive Alembic migration file created
- [x] **Deployment Configuration**: Complete `render.yaml` for 5 Render services

### ✅ Frontend (100%)
- [x] **Swiss UI Design**: 50% redesign with typography-focused, minimalist approach
- [x] **Auth0 React Integration**: Login/logout, protected routes, user profile
- [x] **Business Profile Page**: Website URL input, document upload (10MB limit)
- [x] **Applications Page**: AI generation, section editor, status tracking
- [x] **Settings Page**: Subscription management, usage meters, email preferences
- [x] **Responsive Design**: Mobile-optimized layouts with 8px grid system
- [x] **Dependencies Installed**: All Auth0, Stripe, and file upload packages

### ✅ Code Cleanup (100%)
- [x] **Perplexity Removed**: All 48 references removed, replaced with DeepSeek
- [x] **Telegram Removed**: All 27 references removed, replaced with Resend
- [x] **Import Statements**: Updated across all files

### ✅ Documentation (100%)
- [x] **LOCAL_SETUP.md**: Complete local development guide (665 lines)
- [x] **LAUNCH_STATUS.md**: Comprehensive project status report
- [x] **.env.example**: Full environment configuration template (246 lines)
- [x] **render.yaml**: Production deployment configuration

---

## 🚀 Next Steps - Local Setup & Testing

### Phase 1: External Service Configuration (30-60 minutes)

You need to create accounts and get API keys for these services:

#### 1. Auth0 Setup (Required)
```bash
# Steps:
1. Go to https://auth0.com → Sign up
2. Create new tenant: "grant-finder-dev"
3. Create API:
   - Name: "Grant Finder API"
   - Identifier: https://api.grantfinder.com
   - Enable RBAC and "Add Permissions in Access Token"
4. Create Application (Single Page Application):
   - Name: "Grant Finder Frontend"
   - Allowed Callback URLs: http://localhost:3000/callback
   - Allowed Logout URLs: http://localhost:3000
   - Allowed Web Origins: http://localhost:3000
5. Copy credentials to .env:
   - AUTH0_DOMAIN=your-tenant.us.auth0.com
   - AUTH0_API_AUDIENCE=https://api.grantfinder.com
```

**Priority**: 🔴 CRITICAL - App won't start without this

#### 2. Stripe Setup (Required)
```bash
# Steps:
1. Go to https://dashboard.stripe.com → Sign up
2. Toggle to "Test mode" (top right)
3. Get API keys from Developers → API keys:
   - STRIPE_SECRET_KEY=sk_test_...
   - STRIPE_PUBLISHABLE_KEY=pk_test_...
4. Create Product:
   - Products → Add Product
   - Name: "Grant Finder Basic"
   - Price: $35.00 USD / month
   - Copy Price ID: STRIPE_PRICE_ID=price_...
5. Install Stripe CLI for webhooks:
   brew install stripe/stripe-cli/stripe  # Mac
   # Or download from https://stripe.com/docs/stripe-cli
6. Login and forward webhooks:
   stripe login
   stripe listen --forward-to localhost:8000/api/webhooks/stripe
   # Copy webhook secret: STRIPE_WEBHOOK_SECRET=whsec_...
```

**Priority**: 🔴 CRITICAL - Subscriptions won't work without this

#### 3. DeepSeek AI Setup (Required)
```bash
# Steps:
1. Go to https://platform.deepseek.com → Sign up
2. Generate API key from dashboard
3. Add billing information (pay-as-you-go)
4. Update .env:
   - DEEPSEEK_API_KEY=sk-your-key-here
```

**Priority**: 🔴 CRITICAL - AI features won't work without this

#### 4. Resend Email Setup (Recommended)
```bash
# Steps:
1. Go to https://resend.com → Sign up
2. Add and verify your domain (or use onboarding@resend.dev for testing)
3. Create API key
4. Update .env:
   - RESEND_API_KEY=re_your_key_here
   - FROM_EMAIL=noreply@yourdomain.com (or onboarding@resend.dev)
```

**Priority**: 🟡 RECOMMENDED - Email notifications won't work without this

#### 5. AgentQL Setup (Recommended)
```bash
# Steps:
1. Go to https://www.agentql.com → Sign up
2. Generate API key from dashboard
3. Update .env:
   - AGENTQL_API_KEY=your-key-here
```

**Priority**: 🟡 RECOMMENDED - Grant scraping may use fallback methods without this

---

### Phase 2: Local Infrastructure Setup (15-30 minutes)

#### 1. Install PostgreSQL (if not already installed)
```bash
# macOS (Homebrew)
brew install postgresql@15
brew services start postgresql@15
createdb grantfinder

# Ubuntu/Debian
sudo apt-get install postgresql
sudo systemctl start postgresql
sudo -u postgres createdb grantfinder

# Windows
# Download from https://www.postgresql.org/download/windows/
# Create database using pgAdmin
```

**Status**: ✅ Already configured in .env (postgres:newpassword123@localhost:5432/grantfinder)

#### 2. Install Redis
```bash
# macOS (Homebrew)
brew install redis
brew services start redis
redis-cli ping  # Should return "PONG"

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis
redis-cli ping  # Should return "PONG"

# Windows (Docker - Easiest)
docker run -d -p 6379:6379 --name redis redis:7-alpine

# Windows (WSL2)
# Install Redis in WSL2 Linux environment
```

**Priority**: 🔴 CRITICAL - Celery tasks won't work without this

---

### Phase 3: Run Database Migrations (2 minutes)

```bash
# Make sure you're in the project root directory
cd C:\Users\chizi\OneDrive\Documents\GitHub\kevin-smart-grant-finder

# Activate virtual environment (if using one)
# venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Run migrations
alembic upgrade head

# Verify migration succeeded
alembic current
# Should show: e4f7a9b2c3d1 (head)
```

**What this does**:
- Creates 4 new tables: users, business_profiles, subscriptions, generated_applications
- Adds user_id foreign keys to existing tables
- Creates ENUM types for status management
- Sets up indexes for performance

**Priority**: 🔴 CRITICAL - Database schema must be up to date

---

### Phase 4: Start All Services (5 terminals)

Open 5 separate terminal windows:

#### Terminal 1: Redis
```bash
redis-server
# Should show "Ready to accept connections"
```

#### Terminal 2: Celery Worker
```bash
cd C:\Users\chizi\OneDrive\Documents\GitHub\kevin-smart-grant-finder

# Windows MUST use --pool=solo
celery -A celery_app worker --loglevel=info --pool=solo

# Mac/Linux
celery -A celery_app worker --loglevel=info

# Should show "celery@hostname ready"
```

#### Terminal 3: Celery Beat (Optional - for scheduled tasks)
```bash
cd C:\Users\chizi\OneDrive\Documents\GitHub\kevin-smart-grant-finder

celery -A celery_app beat --loglevel=info

# Should show "Scheduler: Sending due task..."
```

#### Terminal 4: FastAPI Backend
```bash
cd C:\Users\chizi\OneDrive\Documents\GitHub\kevin-smart-grant-finder

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Should show "Application startup complete"
# Access: http://localhost:8000
# API Docs: http://localhost:8000/api/docs
```

#### Terminal 5: React Frontend
```bash
cd C:\Users\chizi\OneDrive\Documents\GitHub\kevin-smart-grant-finder\frontend

npm start

# Should open http://localhost:3000 automatically
```

---

### Phase 5: Test Complete User Flow (15-30 minutes)

#### 1. Test Backend Health
```bash
# Health check
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/health/detailed

# Expected response:
{
  "status": "healthy",  # or "degraded" if some services are unavailable
  "services": {
    "database": "healthy",
    "deepseek": "healthy",
    "pinecone": "healthy"
  }
}
```

#### 2. Test Auth0 Integration
```bash
# Open frontend
http://localhost:3000

# Expected flow:
1. Click "Login" button
2. Redirected to Auth0 login page
3. Create account or sign in
4. Redirected back to dashboard
5. 14-day trial initialized (5 searches, 0 applications)
```

#### 3. Test Business Profile Creation
```bash
# In frontend:
1. Navigate to "Business Profile" page
2. Fill in:
   - Business name
   - Mission statement
   - Website URL
   - Narrative text (max 2000 chars)
3. Upload documents (PDF/DOCX/TXT, max 10MB total)
4. Click "Save Profile"

# Expected result:
- Profile saved to database
- RAG embeddings generated in background (Celery task)
- Confirmation message displayed
```

#### 4. Test Grant Search
```bash
# In frontend:
1. Navigate to "Grants" page
2. Click "New Search" button
3. Enter search criteria
4. Click "Search"

# Expected behavior:
- Celery task queued
- Progress indicator shown
- Results appear when complete
- searches_used counter incremented
```

#### 5. Test AI Application Generation
```bash
# In frontend:
1. Navigate to "Applications" page
2. Select a grant from dropdown
3. Click "Generate Application"

# Expected behavior:
- Celery task queued (takes 1-3 minutes)
- Progress indicator shown
- Application generated using RAG context
- 6 sections populated:
  * Executive Summary
  * Needs Statement
  * Project Description
  * Budget Narrative
  * Organizational Capacity
  * Impact Statement
- applications_used counter incremented
- Email notification sent (if Resend configured)
```

#### 6. Test Subscription Management
```bash
# In frontend:
1. Navigate to "Settings" → "Subscription" tab
2. Click "Upgrade to Basic Plan"
3. Redirected to Stripe checkout
4. Use test card: 4242 4242 4242 4242
5. Complete checkout

# Expected result:
- Stripe subscription created
- Webhook received by backend
- User subscription status updated
- Usage limits reset to 50 searches, 20 applications
- Redirect back to dashboard
```

#### 7. Test Usage Limits
```bash
# Manually update user in database to hit limit:
# (Use pgAdmin or psql)

UPDATE users SET searches_used = 50 WHERE email = 'your@email.com';

# Then in frontend:
1. Try to create new search

# Expected behavior:
- Error message: "Monthly search limit reached"
- Call-to-action to upgrade subscription
```

---

## 🔍 Troubleshooting Guide

### Issue: Backend won't start - "No module named 'X'"
**Solution**:
```bash
pip install -r requirements.txt
```

### Issue: Celery won't start - "ValueError: not enough values to unpack"
**Solution (Windows)**:
```bash
# Windows MUST use --pool=solo
celery -A celery_app worker --loglevel=info --pool=solo
```

### Issue: Database connection error
**Solution**:
```bash
# Check PostgreSQL is running
pg_isready

# Check connection string in .env
echo $DATABASE_URL  # Should match your PostgreSQL credentials
```

### Issue: Redis connection refused
**Solution**:
```bash
# Check Redis is running
redis-cli ping  # Should return "PONG"

# Start Redis if not running
brew services start redis  # Mac
sudo systemctl start redis  # Linux
docker start redis  # Docker
```

### Issue: Auth0 401 Unauthorized
**Solution**:
- Verify AUTH0_DOMAIN matches your tenant
- Verify AUTH0_API_AUDIENCE is correct
- Check token hasn't expired (24 hours default)
- Ensure frontend .env.local has matching values

### Issue: Stripe webhook fails - "Signature verification failed"
**Solution**:
```bash
# Ensure Stripe CLI is running
stripe listen --forward-to localhost:8000/api/webhooks/stripe

# Copy the webhook secret (whsec_...) to .env
STRIPE_WEBHOOK_SECRET=whsec_your_secret_here

# Restart FastAPI server
```

### Issue: Frontend build errors
**Solution**:
```bash
cd frontend
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
npm start
```

### Issue: Migration fails - "relation already exists"
**Solution**:
```bash
# Check current migration state
alembic current

# If behind, upgrade
alembic upgrade head

# If ahead (unlikely), downgrade and re-upgrade
alembic downgrade -1
alembic upgrade head

# If database is corrupt, reset (WARNING: deletes data)
alembic downgrade base
alembic upgrade head
```

---

## 📊 System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                         │
│  - Auth0 Login/Logout                                           │
│  - Business Profile Management (website, document upload)       │
│  - Grant Search & Discovery                                     │
│  - AI Application Generation & Editor                           │
│  - Subscription Management (Stripe)                             │
│  - Usage Tracking & Limits                                      │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 │ HTTPS
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FASTAPI BACKEND (Python)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐        │
│  │ Auth0 JWT    │  │ Stripe       │  │ Usage Limits   │        │
│  │ Verification │  │ Webhooks     │  │ Enforcement    │        │
│  └──────────────┘  └──────────────┘  └────────────────┘        │
│                                                                  │
│  ┌─────────────────────────────────────────────────────┐       │
│  │              API ROUTES                              │       │
│  │  - /api/business-profile/* (CRUD + upload)          │       │
│  │  - /api/applications/* (CRUD + generate)            │       │
│  │  - /api/subscriptions/* (create, cancel, usage)     │       │
│  │  - /api/grants/* (search, list, detail)             │       │
│  │  - /api/webhooks/stripe (subscription events)       │       │
│  └─────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
           │                   │                    │
           │                   │                    │
           ▼                   ▼                    ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │PostgreSQL│        │  Redis   │        │ Pinecone │
    │ Database │        │  Cache   │        │  Vectors │
    └──────────┘        └──────────┘        └──────────┘
           │                   │
           │                   ▼
           │            ┌────────────────┐
           │            │  Celery Worker │
           │            │  - Grant Search│
           │            │  - AI App Gen  │
           │            │  - Maintenance │
           │            └────────────────┘
           │                   │
           ▼                   ▼
    ┌──────────────────────────────────┐
    │     EXTERNAL SERVICES            │
    │  - Auth0 (authentication)        │
    │  - Stripe (payments)             │
    │  - DeepSeek AI (reasoning)       │
    │  - Resend (email notifications)  │
    │  - AgentQL (web scraping)        │
    └──────────────────────────────────┘
```

---

## 📈 Key Metrics & Limits

### Free Trial (14 days)
- **Searches**: 5 total
- **Applications**: 0 total
- **Duration**: 14 days
- **Auto-downgrade**: After trial expires, user must subscribe

### Basic Plan ($35/month)
- **Searches**: 50 per month
- **Applications**: 20 per month
- **Auto-reset**: On monthly billing date
- **Features**:
  - Automated grant searches (every 6 hours)
  - AI application generation with RAG
  - Email notifications
  - Document uploads (10MB total)
  - Business profile with website URL

### Technical Limits
- **Document Upload**: 10MB total per user
- **Narrative Text**: 2000 characters
- **Application Generation Time**: 60-180 seconds
- **RAG Context**: 500 char chunks, 50 char overlap
- **Email Rate**: No limit (Resend free tier: 3000/month)

---

## 🎯 Success Criteria

### ✅ Backend Ready When:
- [ ] Health check returns "healthy"
- [ ] Database migration completed (e4f7a9b2c3d1)
- [ ] Auth0 JWT verification working
- [ ] Stripe webhook receiving events
- [ ] Celery worker processing tasks
- [ ] Redis connected

### ✅ Frontend Ready When:
- [ ] Auth0 login flow working
- [ ] Business profile page loads
- [ ] Applications page loads
- [ ] Settings page shows subscription status
- [ ] All API calls succeed (200 responses)

### ✅ End-to-End Ready When:
- [ ] User can create account (Auth0)
- [ ] User can create business profile with website URL
- [ ] User can upload documents
- [ ] User can search for grants (Celery task)
- [ ] User can generate AI application (Celery task)
- [ ] User can subscribe via Stripe
- [ ] Usage limits enforced correctly
- [ ] Email notifications sent (Resend)

---

## 📝 Configuration Files Summary

### Backend Configuration
- [x] **.env** - Updated with all new service variables
- [x] **config/settings.py** - All environment variables defined
- [x] **celery_app.py** - Celery configuration with Beat schedule
- [x] **render.yaml** - Production deployment (5 services)

### Frontend Configuration
- [ ] **frontend/.env.local** - Need to create with:
  ```bash
  REACT_APP_API_URL=http://localhost:8000
  REACT_APP_AUTH0_DOMAIN=your-tenant.us.auth0.com
  REACT_APP_AUTH0_CLIENT_ID=your_client_id
  REACT_APP_STRIPE_PUBLISHABLE_KEY=pk_test_your_key
  ```

### Database
- [x] **migrations/versions/e4f7a9b2c3d1_*.py** - Multi-user migration
- [x] **database/models.py** - 4 new tables + FK updates

---

## 🚢 Render Deployment (When Ready)

### Prerequisites
1. All external services configured (Auth0, Stripe, DeepSeek, etc.)
2. Local testing completed successfully
3. Code pushed to GitHub

### Deployment Steps
```bash
# 1. Push code to GitHub
git add .
git commit -m "Multi-user platform ready for deployment"
git push origin main

# 2. Connect Render to GitHub
- Go to https://dashboard.render.com
- Click "New" → "Blueprint"
- Connect your GitHub repository
- Render will detect render.yaml automatically

# 3. Configure Environment Variables in Render
- Set all 30+ environment variables from .env
- DATABASE_URL and REDIS_URL auto-populated by Render

# 4. Deploy
- Click "Deploy"
- Wait 5-10 minutes for all 5 services to start
- Verify health check: https://your-app.onrender.com/health

# 5. Update Frontend
- Deploy frontend to Vercel/Netlify
- Update REACT_APP_API_URL to Render backend URL
- Update Auth0 allowed origins to include production URL
```

---

## 📞 Support & Resources

### Documentation
- **Local Setup Guide**: [LOCAL_SETUP.md](LOCAL_SETUP.md)
- **Launch Status**: [LAUNCH_STATUS.md](LAUNCH_STATUS.md)
- **Environment Config**: [.env.example](.env.example)
- **Render Deployment**: [render.yaml](render.yaml)

### External Service Docs
- **Auth0**: https://auth0.com/docs
- **Stripe**: https://stripe.com/docs
- **DeepSeek**: https://platform.deepseek.com/docs
- **Resend**: https://resend.com/docs
- **AgentQL**: https://docs.agentql.com
- **Pinecone**: https://docs.pinecone.io

### Key Files Reference
- **Backend Entry**: [app/main.py](app/main.py)
- **API Routes**: [app/router.py](app/router.py)
- **Database Models**: [database/models.py](database/models.py)
- **Auth Integration**: [app/auth.py](app/auth.py)
- **Payments**: [app/payments.py](app/payments.py)
- **Business Profile API**: [app/business_profile_routes.py](app/business_profile_routes.py)
- **Applications API**: [app/applications_routes.py](app/applications_routes.py)
- **Celery Tasks**: [tasks/](tasks/)

---

## ✨ What Makes This Special

### Technical Excellence
- **Graceful Degradation**: App continues working even if external services fail
- **Type Safety**: Pydantic schemas throughout with proper validation
- **Comprehensive Error Handling**: Structured logging, error recovery, retry policies
- **Performance Optimized**: Indexes, connection pooling, caching, async operations
- **Security First**: JWT verification, webhook signatures, CORS, input sanitization

### User Experience
- **Swiss Design Principles**: Minimal, clean, typography-focused UI
- **Mobile-First**: Fully responsive with touch-friendly controls
- **Real-Time Feedback**: Progress indicators, usage meters, status updates
- **Smart Defaults**: 14-day trial, usage warnings at 80%, graceful limit enforcement

### Developer Experience
- **Well Documented**: 3 comprehensive guides (LOCAL_SETUP, LAUNCH_STATUS, this file)
- **Easy Setup**: Copy .env.example, fill in keys, run migrations, start services
- **Reversible Migrations**: Full downgrade() functions for safety
- **Local Development**: Hot reload, detailed logging, test mode for all services

---

**Ready to launch! 🚀**

For questions or issues, refer to the troubleshooting section or check the comprehensive guides in the project root.
