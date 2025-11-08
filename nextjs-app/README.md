# 🚀 Smart Grant Finder v2.0 - Multi-Tenant SaaS

AI-powered grant discovery platform with chat interface, automated searches, and one-click applications.

---

## 📋 Overview

Smart Grant Finder v2.0 is a complete rebuild transforming the original personal grant finder into a **multi-tenant SaaS platform** with:

- 💬 **Chat-centric interface** using Vercel AI SDK
- 💰 **Pay-as-you-go credit system** with transparent pricing
- 🤖 **DeepSeek AI integration** (95% cost savings vs Perplexity)
- 🌐 **AgentQL web scraping** with virtual desktop
- 👤 **Admin user management** with whitelisting workflow
- 💳 **Stripe payment processing**
- 📧 **Automated email notifications**
- 📁 **Document upload & AI analysis**
- ⏰ **Automated cron-based searches**

---

## 🎯 Key Features

### For Users
- ✨ AI-powered grant discovery via natural language chat
- 🔍 Multi-source grant aggregation (Grants.gov, foundations, etc.)
- 📊 Intelligent scoring and filtering
- 📅 Deadline tracking and reminders
- 📝 One-click application assistance
- 💳 Transparent credit-based pricing
- ⏰ Automated daily grant searches (up to 2x/day)

### For Admins
- 👥 User whitelist management
- 📈 Platform analytics and cost tracking
- 💰 Revenue monitoring
- 🔐 Role-based access control (RBAC)

---

## 💻 Tech Stack

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **UI**: Tailwind CSS + shadcn/ui
- **Chat**: Vercel AI SDK
- **State**: React Hooks + Server Components

### Backend
- **API**: Next.js API Routes
- **Database**: PostgreSQL (Prisma ORM)
- **Auth**: NextAuth.js v5
- **Payments**: Stripe
- **Email**: Resend
- **Storage**: Cloudflare R2

### AI & Services
- **AI**: DeepSeek ($0.14-0.28 per 1M tokens)
- **Web Scraping**: AgentQL (virtual desktop)
- **Embeddings**: OpenAI text-embedding-3-large
- **Vector DB**: Pinecone
- **Cron**: Vercel Cron

---

## 📁 Project Structure

```
nextjs-app/
├── app/                      # Next.js App Router
│   ├── api/                  # API routes
│   │   ├── auth/            # Authentication endpoints
│   │   ├── credits/         # Credit operations
│   │   ├── payments/        # Stripe webhooks
│   │   ├── search/          # Grant search
│   │   └── chat/            # Chat interface
│   ├── chat/                # Main chat page
│   ├── admin/               # Admin dashboard
│   ├── dashboard/           # User dashboard
│   └── auth/                # Auth pages
│
├── lib/                     # Core libraries
│   ├── services/            # Service layer
│   │   ├── deepseek.ts     # DeepSeek AI client
│   │   ├── agentql.ts      # AgentQL scraping
│   │   ├── credit-manager.ts  # Credit system
│   │   ├── stripe.ts       # Stripe payments
│   │   ├── resend.ts       # Email service
│   │   ├── r2-storage.ts   # Document storage
│   │   └── cost-tracker.ts # API cost tracking
│   ├── utils/               # Utility functions
│   ├── validations/         # Zod schemas
│   └── prisma.ts            # Prisma client
│
├── components/              # React components
│   ├── ui/                  # shadcn/ui components
│   ├── chat/                # Chat interface
│   ├── admin/               # Admin components
│   └── grant/               # Grant cards, comparison
│
├── prisma/
│   └── schema.prisma        # Database schema (12 models)
│
├── __tests__/               # Test suites
│   ├── services/            # Service tests
│   └── components/          # Component tests
│
├── auth.ts                  # NextAuth config
├── auth.config.ts           # Auth callbacks
├── middleware.ts            # Route protection
└── package.json             # Dependencies
```

---

## 🗄️ Database Schema

### Core Models (12)

1. **User** - User accounts with RBAC
   - Roles: ADMIN, USER
   - Whitelist status: PENDING, APPROVED, REJECTED, BLOCKED
   - Profile: organization type, grant preferences, funding range

2. **Credit** - User credit balance
   - Tier 1: $10 = 10 credits
   - Tier 2: $20 = 22 credits (11% bonus)
   - Lifetime tracking

3. **CreditTransaction** - All credit movements
   - Types: DEPOSIT, DEDUCTION, REFUND, BONUS
   - Full audit trail

4. **Document** - Uploaded files (50MB max)
   - Types: RESUME, CV, ORG_PROFILE, PAST_APPLICATION
   - R2 storage with metadata

5. **Grant** - Grant opportunities
   - Scoring: relevance, deadline, funding, final
   - Status: ACTIVE, EXPIRED, DRAFT, ARCHIVED

6. **GrantSearch** - Search execution logs
   - Trigger: MANUAL (chat), CRON (scheduled)
   - Cost breakdown per service
   - Real-time logs

7. **UserSettings** - User preferences
   - Cron schedule (max 2x/day)
   - Notification preferences
   - Search filters

8. **Application** - Grant application tracking
   - Status: DRAFT → IN_PROGRESS → SUBMITTED → ACCEPTED/REJECTED
   - AI-generated drafts

9. **ChatHistory** - Conversation threads
   - Max 50 messages per thread
   - Max 10 threads per user

10. **APIUsageLog** - All API calls
    - Services: DEEPSEEK, AGENTQL, OPENAI, PINECONE, STRIPE, RESEND, R2
    - Cost tracking

11. **Account** - Auth.js accounts
12. **Session** - Auth.js sessions

---

## 💰 Pricing & Credits

### Credit System
- **1 credit = $1** (charged to user)
- **Actual cost × 1.5** = credited amount deducted
- **Block usage** when balance ≤ $0
- **Negative balance** allowed during search execution

### Pricing Tiers
```
Tier 1:  $10 → 10 credits (1:1)
Tier 2:  $20 → 22 credits (11% bonus)
Top-up:  $5 minimum (1:1)
```

### Cost Estimates
Average grant search:
- DeepSeek: ~$0.0005 (2k tokens)
- AgentQL: ~$0.03 (3 pages)
- OpenAI: ~$0.0001 (embeddings)
- **Total**: ~$0.03 actual → ~$0.045 charged (1.5x)

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- PostgreSQL database
- API Keys (see below)

### Installation

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Configure Environment**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add:
   - ✅ `DEEPSEEK_API_KEY` (provided)
   - ✅ `AGENTQL_API_KEY` (provided)
   - `DATABASE_URL` (PostgreSQL connection string)
   - `AUTH_SECRET` (generate with `openssl rand -base64 32`)
   - `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`
   - `RESEND_API_KEY` (get at https://resend.com)
   - `R2_*` variables (Cloudflare R2 configuration)

3. **Set Up Database**
   ```bash
   npx prisma generate
   npx prisma migrate dev --name init
   ```

4. **Run Development Server**
   ```bash
   npm run dev
   ```

   Open [http://localhost:3000](http://localhost:3000)

---

## 🔑 API Keys Setup

### DeepSeek ✅
- **Key**: `sk-96d37eb6c4e44e6ebb8c28d892b565d1`
- **URL**: https://api.deepseek.com
- **Cost**: $0.14/M input, $0.28/M output tokens

### AgentQL ✅
- **Key**: `u_ULLZKn3-dJbWiDHp9bPoBhKtpG1abrzdJIYlXjLrwd8VzqL_hBaw`
- **Use**: Web scraping with virtual desktop

### Stripe ⏳
1. Sign up at https://stripe.com
2. Get test keys from Dashboard → Developers → API keys
3. Set up webhook at Dashboard → Developers → Webhooks
   - Endpoint: `https://your domain.com/api/webhooks/stripe`
   - Events: `checkout.session.completed`

### Resend ⏳
1. Sign up at https://resend.com/signup
2. Add your domain or use `onboarding@resend.dev` for testing
3. Get API key from Dashboard → API Keys

### Cloudflare R2 ⏳
1. Log in to Cloudflare Dashboard
2. Go to R2 → Create bucket → `grant-finder-documents`
3. Create API token → R2 Read & Write
4. Get Account ID, Access Key, Secret Key

---

## 🧪 Testing

### Run Unit Tests
```bash
npm test
```

### Run E2E Tests
```bash
npm run test:e2e
```

### Test Coverage
```bash
npm run test:coverage
```

---

## 📦 Deployment

### Vercel (Recommended)

1. **Push to GitHub**
   ```bash
   git push origin main
   ```

2. **Import to Vercel**
   - Go to https://vercel.com/new
   - Import your repository
   - Configure environment variables
   - Deploy!

3. **Configure Database**
   - Use existing Heroku PostgreSQL
   - Update `DATABASE_URL` in Vercel env vars

4. **Set Up Webhooks**
   - Stripe webhook → `/api/webhooks/stripe`
   - Add webhook secret to env vars

---

## 📊 Cost Breakdown

### Monthly Operating Costs

**AI Services:**
- DeepSeek: ~$10-20/month (100k searches)
- AgentQL: ~$20-30/month (subscription)
- OpenAI: ~$5-10/month (embeddings)
- **Total**: ~$35-60/month

**Infrastructure:**
- Vercel: Free (Pro: $20/month if needed)
- PostgreSQL: $0 (using existing Heroku)
- Cloudflare R2: ~$0-5/month
- Stripe: 2.9% + $0.30 per transaction
- Resend: Free up to 3k emails/month

**Total Platform Cost**: ~$35-65/month

**Revenue Potential** (100 users @ $10/month):
- Gross: $1,000/month
- Costs: ~$50/month
- **Net**: ~$950/month 🎉

---

## 🔒 Security

- ✅ NextAuth.js v5 for authentication
- ✅ JWT session management
- ✅ RBAC (Admin/User roles)
- ✅ Whitelist approval workflow
- ✅ Row-level security via Prisma
- ✅ Input validation (Zod)
- ✅ CSRF protection
- ✅ Secure environment variables

---

## 📖 Chat Limits

- **Max messages per thread**: 50
- **Max threads per user**: 10
- **Auto-archive** when thread reaches 50 messages
- **Full system access** from any chat

---

## 🛣️ Roadmap

### Phase 1: Foundation ✅
- [x] Next.js project setup
- [x] Database schema design
- [x] Core services (DeepSeek, AgentQL, etc.)
- [x] Credit system
- [x] Authentication configuration

### Phase 2: API & UI (In Progress) 🚧
- [ ] API routes implementation
- [ ] shadcn/ui setup
- [ ] Chat interface
- [ ] Admin dashboard
- [ ] Document upload

### Phase 3: Features 📋
- [ ] Grant comparison tool
- [ ] PDF export
- [ ] One-click applications
- [ ] Calendar view
- [ ] Cron jobs

### Phase 4: Testing & Deployment 🧪
- [ ] Unit tests (80%+ coverage)
- [ ] E2E tests
- [ ] Production deployment
- [ ] Monitoring setup

---

## 📞 Support

For questions or issues:
- Check BUILD_PROGRESS.md for current status
- Review this README for setup instructions
- Contact: [Your email]

---

## 📄 License

Proprietary - All rights reserved

---

**Built with ❤️ using Next.js, DeepSeek AI, and AgentQL**
