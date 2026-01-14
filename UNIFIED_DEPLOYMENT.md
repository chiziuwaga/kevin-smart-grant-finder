# Unified Render Deployment Guide

## 🎯 Architecture: Single Service Deployment

**All-in-One Render Service:**
```
https://kevin-smart-grant-finder.onrender.com
  ├── /              → React Frontend (static files)
  ├── /api/*         → FastAPI Backend APIs
  ├── /docs          → API Documentation
  └── /health        → Health Check
```

### Benefits of Unified Deployment:
✅ **Simpler**: One service instead of two separate deployments
✅ **Cheaper**: ~$7-25/month instead of $14-50/month
✅ **No CORS issues**: Same-origin, no cross-domain requests
✅ **Faster**: No network latency between frontend/backend
✅ **Easier auth**: Session cookies work automatically
✅ **Single domain**: No need for separate Vercel configuration

---

## 🏗️ How It Works

### Build Process (Automatic on Render)
```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Install Node.js and build React frontend
cd frontend
npm install
npm run build
cd ..

# 3. FastAPI serves both:
#    - Static files from frontend/build/
#    - API endpoints from /api/*
```

### Request Routing
```
GET /                    → React index.html
GET /dashboard           → React index.html (SPA routing)
GET /grants              → React index.html (SPA routing)
GET /static/...          → React static assets (JS, CSS, images)

GET /api/grants          → FastAPI backend
POST /api/search-runs    → FastAPI backend
GET /health              → FastAPI health check
GET /docs                → FastAPI Swagger docs
```

---

## 📋 Deployment Steps

### Step 1: Connect Repository to Render

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Blueprint"**
3. Connect GitHub repository: `chiziuwaga/kevin-smart-grant-finder`
4. Render will detect [render.yaml](render.yaml) and create 5 services:
   - ✅ **grant-finder-api** (web service - serves frontend + API)
   - ✅ **grant-finder-worker** (Celery background tasks)
   - ✅ **grant-finder-scheduler** (Celery Beat cron jobs)
   - ✅ **grant-finder-db** (PostgreSQL database)
   - ✅ **grant-finder-redis** (Redis for Celery)

### Step 2: Set Required Environment Variables

In Render dashboard, go to **grant-finder-api** → **Environment** tab.

Add these **9 required variables**:

```bash
# Auth0 (https://auth0.com)
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_API_AUDIENCE=https://api.grantfinder.com

# Stripe (https://dashboard.stripe.com)
STRIPE_SECRET_KEY=sk_live_...  # OR sk_test_... for testing
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...  # Your $35/month price ID

# Resend Email (https://resend.com)
RESEND_API_KEY=re_...

# DeepSeek AI (https://platform.deepseek.com)
DEEPSEEK_API_KEY=sk-...

# AgentQL (https://www.agentql.com)
AGENTQL_API_KEY=agentql_...
```

**Use your existing keys from .env file:**
```bash
# Pinecone (copy from your .env)
PINECONE_API_KEY=pcsk_...

# OpenAI (copy from your .env)
OPENAI_API_KEY=sk-proj-...
```

### Step 3: Configure Auth0

1. Create Auth0 tenant at https://auth0.com
2. Create **Single Page Application**
3. Add Allowed Callback URLs:
   ```
   https://kevin-smart-grant-finder.onrender.com
   http://localhost:3000
   ```
4. Add Allowed Logout URLs:
   ```
   https://kevin-smart-grant-finder.onrender.com
   http://localhost:3000
   ```
5. Add Allowed Web Origins:
   ```
   https://kevin-smart-grant-finder.onrender.com
   http://localhost:3000
   ```
6. Create **API** in Auth0 with identifier: `https://api.grantfinder.com`
7. Copy **Domain** → Use as `AUTH0_DOMAIN` in Render
8. Copy **Client ID** (not needed for backend, only for frontend Auth0 setup)

### Step 4: Configure Stripe Webhook

1. In Stripe Dashboard: **Developers** → **Webhooks** → **Add endpoint**
2. Endpoint URL:
   ```
   https://kevin-smart-grant-finder.onrender.com/api/webhooks/stripe
   ```
3. Select events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
4. Copy **Signing secret** → Add to Render as `STRIPE_WEBHOOK_SECRET`

### Step 5: Deploy!

Once all environment variables are set:
1. Render will auto-deploy from your GitHub push
2. Build process takes ~5-8 minutes:
   - Install Python deps (2 min)
   - Install Node deps (2 min)
   - Build React app (1 min)
   - Start Gunicorn + Uvicorn (1 min)
3. Check deployment logs in Render dashboard

### Step 6: Run Database Migration

After deployment succeeds, run Alembic migration:

**Option A: Via Render Shell**
```bash
# In Render dashboard: grant-finder-api → Shell tab
alembic upgrade head
```

**Option B: Via Render MCP** (if configured)
```bash
# Just ask Claude Code:
"Run alembic upgrade head on Render"
```

### Step 7: Verify Deployment

Check these endpoints:

✅ **Frontend**: https://kevin-smart-grant-finder.onrender.com
✅ **Health Check**: https://kevin-smart-grant-finder.onrender.com/health
✅ **API Docs**: https://kevin-smart-grant-finder.onrender.com/docs
✅ **API Health**: https://kevin-smart-grant-finder.onrender.com/health/detailed

---

## 🔧 Configuration Details

### Frontend Build Configuration

No changes needed! The React app already defaults to `/api`:

```typescript
// frontend/src/api/apiClient.ts
baseURL: process.env.REACT_APP_API_URL || '/api'
```

When `REACT_APP_API_URL` is not set (which it won't be in production), all API calls automatically use relative URLs: `/api/grants`, `/api/search-runs`, etc.

### CORS Configuration

Since frontend and backend are on the same origin, CORS is minimal:

```python
# app/main.py
# In production: only localhost allowed (for local testing)
# No need for cross-origin since same domain
```

### Static File Serving

FastAPI serves the React build:

```python
# app/main.py
frontend_build_path = Path(__file__).parent.parent / "frontend" / "build"

# Mount static assets
app.mount("/static", StaticFiles(directory=frontend_build_path / "static"))

# Serve index.html for all non-API routes (SPA routing)
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    if not full_path.startswith("api/"):
        return FileResponse(frontend_build_path / "index.html")
```

---

## 📊 Cost Breakdown

### Monthly Costs:

| Service | Plan | Cost |
|---------|------|------|
| Web (API + Frontend) | Starter | $7 |
| PostgreSQL | Starter (1GB) | $7 |
| Redis | Starter (25MB) | Free |
| Celery Worker | Starter | $7 |
| **Total** | | **$21/month** |

**Compare to separate deployments:**
- Render Backend: $7-25/month
- Vercel Frontend: $0-20/month
- Total: $7-45/month

**Savings: ~$0-24/month** (and much simpler!)

---

## 🚀 Auto-Deploy Configuration

Already configured! Every push to `master` branch automatically triggers deployment.

### GitHub → Render Auto-Deploy Flow:

1. You push code to GitHub
2. GitHub webhook notifies Render
3. Render pulls latest code
4. Render runs build command:
   ```bash
   pip install -r requirements.txt &&
   cd frontend &&
   npm install &&
   npm run build &&
   cd ..
   ```
5. Render restarts service with new code
6. Your app is live! 🎉

### Monitor Deployments:

- **Render Dashboard**: https://dashboard.render.com
- **GitHub Actions**: See deployment status in commits
- **Render MCP** (optional): Monitor from Claude Code

---

## 🔍 Troubleshooting

### Build Failures

**"npm: command not found"**
- Render auto-installs Node.js for Python runtime
- If issue persists, add to render.yaml: `NODE_VERSION=18`

**"Frontend not built" message**
- Check build logs for npm errors
- Verify `frontend/package.json` exists
- Check Node.js memory limits (upgrade to Standard plan if needed)

### Deployment Failures

**"Missing environment variable" errors**
- Verify all 9 required env vars are set in Render dashboard
- Check for typos in variable names

**Database connection errors**
- Wait for PostgreSQL service to be healthy (~2-3 minutes on first deploy)
- Check `DATABASE_URL` is auto-populated from render.yaml

**Redis connection errors**
- Wait for Redis service to be healthy
- Check `REDIS_URL` is auto-populated

### Runtime Issues

**Frontend shows but API fails**
- Check `/health` endpoint: https://kevin-smart-grant-finder.onrender.com/health
- Review logs in Render dashboard
- Verify database migration ran: `alembic upgrade head`

**CORS errors in browser console**
- Shouldn't happen with same-origin!
- If seeing CORS errors, check that requests go to `/api/*` not external domain

**404 on page refresh**
- FastAPI should serve index.html for all non-API routes
- Check `serve_frontend` function in app/main.py is registered

---

## 📝 Comparison: Before vs After

### Before (Separate Deployments):
```
Frontend (Vercel)    →  https://app.vercel.app
                         ↓ HTTP Request (CORS)
Backend (Render)     →  https://api.render.com
```

**Issues:**
- ❌ CORS configuration needed
- ❌ Two separate deployments
- ❌ Two domains to manage
- ❌ Cookie/auth complications
- ❌ Higher cost ($7-45/month)
- ❌ More complex setup

### After (Unified):
```
Single Service (Render)  →  https://kevin-smart-grant-finder.onrender.com
                             ├── /         (Frontend)
                             └── /api/*    (Backend)
```

**Benefits:**
- ✅ No CORS needed (same origin)
- ✅ Single deployment
- ✅ One domain to manage
- ✅ Auth/cookies just work
- ✅ Lower cost ($21/month)
- ✅ Simpler setup

---

## 🎯 Next Steps After Deployment

1. **Test Complete User Flow:**
   - [ ] Visit https://kevin-smart-grant-finder.onrender.com
   - [ ] Sign up/login with Auth0
   - [ ] Subscribe with Stripe
   - [ ] Run grant search
   - [ ] Generate application with AI
   - [ ] Check email notifications

2. **Monitor Performance:**
   - [ ] Check response times in Render dashboard
   - [ ] Monitor Celery task queue
   - [ ] Review error logs
   - [ ] Set up uptime monitoring (UptimeRobot, etc.)

3. **Production Checklist:**
   - [ ] Use Stripe live keys (not test keys)
   - [ ] Verify SSL certificate is active
   - [ ] Set up custom domain (optional)
   - [ ] Configure DNS records (if using custom domain)
   - [ ] Enable Render auto-scaling (if needed)
   - [ ] Set up log aggregation (Sentry, LogDNA, etc.)

4. **Marketing & Launch:**
   - [ ] Add Google Analytics
   - [ ] Create landing page
   - [ ] Set up email sequences
   - [ ] Launch! 🚀

---

## 📚 Additional Resources

- [Render Documentation](https://render.com/docs)
- [FastAPI Static Files](https://fastapi.tiangolo.com/tutorial/static-files/)
- [Auth0 Setup Guide](https://auth0.com/docs/quickstart/spa/react)
- [Stripe Webhooks](https://stripe.com/docs/webhooks)
- [Render MCP Setup](RENDER_MCP_SETUP.md)

---

**Your app is ready for production! 🎉**

All code changes are already committed and pushed. Just set the environment variables in Render and watch it deploy automatically!
