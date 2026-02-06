# Smart Grant Finder - Platform Presentation

**Prepared for:** Kevin Carter
**Prepared by:** Chizi U
**Date:** February 2026

---

## Executive Summary

Smart Grant Finder is a production-ready, AI-powered SaaS platform that automates grant discovery, scoring, and application generation for nonprofits, small businesses, and community organizations. It runs 24/7, searching for grants every 6 hours and notifying users of high-relevance matches via email.

---

## Platform Capabilities

### 1. AI Grant Discovery

- **DeepSeek Reasoning Engine** generates targeted search strategies based on each user's business profile
- **Recursive Chunked Search** breaks discovery into focused queries across federal, state, and foundation databases
- **URL-validated results** - only grants with verifiable application links are surfaced
- **Automatic deduplication** prevents the same grant from appearing twice

### 2. Multi-Dimensional Scoring

Every grant is scored across six dimensions:

| Dimension | What It Measures |
| --- | --- |
| Sector Relevance | How closely the grant matches the user's target sectors |
| Geographic Relevance | Local > state > regional > federal priority |
| Operational Alignment | Team size, revenue range, years in operation |
| Business Logic | Prohibited keywords, ethical red flags, org-type match |
| Feasibility | Budget fit, reporting requirements, technical expertise |
| Strategic Synergy | Alignment with stated organizational objectives |

### 3. Application Generation (RAG-Powered)

- Generates complete grant applications from the user's business profile narrative
- Structured sections: Executive Summary, Needs Statement, Project Description, Budget Narrative, Organizational Capacity, Impact Statement
- Users can review, edit, and track each application through its lifecycle

### 4. Automated Monitoring

- Celery Beat runs grant searches every 6 hours for all active users
- Email notifications sent after every search run (summary + high-priority alerts)
- Weekly digest emails summarize grant activity and upcoming deadlines
- Usage warnings sent when approaching monthly limits

### 5. User Dashboard

- Clean Swiss design with Inter font, minimal color palette
- Filterable grants grid with scoring, deadlines, and bulk actions
- Saved grants, application tracking, search history
- Business profile editor with sector targeting and geographic focus

---

## Technical Architecture

```text
React SPA (Swiss UI)  -->  FastAPI Backend  -->  PostgreSQL + pgvector
                                |
                          Celery + Redis  -->  DeepSeek AI
                                |
                          Resend (Email)
```

- **Single deployment** on Render (API + frontend in one service)
- **PostgreSQL** for all data storage including vector embeddings (pgvector)
- **Redis** for Celery task queue and result backend
- **DeepSeek** for AI reasoning and grant analysis
- **fastembed** (BAAI/bge-small-en-v1.5) for real 384-dim vector embeddings via pgvector
- **Resend** for transactional email (welcome, alerts, reports)

---

## Cost Analysis

### Infrastructure Costs (Render)

| Component | 100 Users | 500 Users |
| --- | --- | --- |
| Web Service (Starter) | $7/mo | $25/mo (Standard) |
| PostgreSQL (Starter) | $7/mo | $25/mo (Standard) |
| Redis (Starter) | $10/mo | $10/mo |
| **Render Total** | **$24/mo** | **$60/mo** |

### AI Costs (DeepSeek)

DeepSeek pricing: $0.14/M input tokens, $0.28/M output tokens

| Metric | 100 Users | 500 Users |
| --- | --- | --- |
| Searches/day (4x/user) | 400 | 2,000 |
| Avg tokens/search | ~5,000 | ~5,000 |
| Monthly token volume | ~60M | ~300M |
| **DeepSeek Cost** | **~$15/mo** | **~$75/mo** |

### Email Costs (Resend)

| Tier | Emails/mo | Cost |
| --- | --- | --- |
| Free tier | 3,000 | $0 |
| Pro tier | 50,000 | $20/mo |

### Total Monthly Cost

| Scale | Infrastructure | AI | Email | Total |
| --- | --- | --- | --- | --- |
| **100 users** | $24 | $15 | $0 | **~$39/mo** |
| **500 users** | $60 | $75 | $20 | **~$155/mo** |

### Revenue Potential

At $15/mo per user (Basic plan):

| Scale | Monthly Revenue | Monthly Cost | Margin |
| --- | --- | --- | --- |
| 100 users | $1,500 | $39 | **$1,461 (97%)** |
| 500 users | $7,500 | $155 | **$7,345 (98%)** |

---

## Subscription Tiers (Proposed)

| Feature | Trial (Free) | Basic ($15/mo) | Pro ($75/mo) |
| --- | --- | --- | --- |
| Grant Searches | 5 total | 50/month | Unlimited |
| AI Applications | 0 | 20/month | Unlimited |
| Automated Monitoring | No | Yes | Yes |
| Email Alerts | Limited | Full | Full + Weekly Reports |
| Business Profiles | 1 | 1 | 3 |
| Priority Support | No | Email | Phone + Email |

---

## Stripe Integration Notes

Stripe integration is scaffolded but not yet configured. To activate:

1. **Create Stripe account** at stripe.com
2. **Create Products & Prices** for Basic ($15/mo) and Pro ($75/mo)
3. **Set environment variables:**
   - `STRIPE_SECRET_KEY` - from Stripe dashboard
   - `STRIPE_PUBLISHABLE_KEY` - for frontend
   - `STRIPE_WEBHOOK_SECRET` - for payment event handling
4. **Webhook endpoint** is already at `POST /api/webhooks/stripe`
5. **Payment service** at `app/payments.py` handles subscription lifecycle
6. Frontend subscription UI at Settings page shows "Stripe billing coming soon"

The platform is designed so that once Stripe keys are added, billing activates without code changes.

---

## What's Included in This Build

- Full-stack deployed application (Render-ready, unified service)
- Auth0 RS256 JWT authentication
- Complete grant search pipeline (DeepSeek + recursive agents + progressive geographic widening)
- Real semantic matching via pgvector + fastembed (384-dim embeddings, HNSW indexes)
- 60-day grant freshness scoring (stale grants auto-marked)
- Email notification system (Resend: welcome, search complete, grant alerts, weekly reports, trial warnings, payment failure)
- React frontend with Swiss design, responsive layout (1024px tablet + 768px mobile breakpoints)
- "Money finder" branded landing page with SVG icons, micro-interactions, and subtle dot-grid background
- Onboarding tooltip system (per-user, replayable, contextual per page)
- Business profile management with vector embeddings for semantic retrieval
- AI application generation (RAG-powered)
- Automated background tasks (Celery Beat: 6-hour search, daily warnings, weekly reports)
- Pre-deploy validation script (checks DB, pgvector, Redis, env vars)
- Database migrations (Alembic)
- Comprehensive README with setup instructions

---

## Partnership & Support

This platform was architected and built by **Chizi U** with a focus on production reliability, graceful degradation, and clean code organization.

**Ongoing support options:**

- Bug fixes and maintenance
- Feature development (new scoring models, additional grant sources)
- Stripe integration activation and testing
- Scaling consultation as user base grows
- Custom integrations (CRM, accounting software)

---

*Smart Grant Finder - Money finder for your business while you sleep.*
