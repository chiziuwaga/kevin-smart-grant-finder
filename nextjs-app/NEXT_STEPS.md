# 🎯 Next Steps - Smart Grant Finder v2.0

**Current Status**: Core infrastructure complete (40%)
**Next Phase**: API Routes + UI Components
**Target**: Production-ready SaaS platform

---

## ✅ COMPLETED (What's Been Built)

### 1. Project Foundation
- ✅ Next.js 14 project structure
- ✅ TypeScript configuration
- ✅ Tailwind CSS setup
- ✅ Environment variables (.env + .env.example)
- ✅ Dependencies installed (package.json)

### 2. Database Architecture
- ✅ **12 Prisma models** designed:
  - User (with RBAC + whitelist)
  - Credit & CreditTransaction
  - Document (R2 storage)
  - Grant & GrantSearch
  - UserSettings
  - Application
  - ChatHistory (50 msg/thread limit)
  - APIUsageLog
  - Account, Session, VerificationToken

### 3. Core Services (7 services)
- ✅ **DeepSeek Client** (`lib/services/deepseek.ts`)
  - Grant search
  - Data extraction
  - Cost calculation ($0.14-0.28/M tokens)

- ✅ **AgentQL Client** (`lib/services/agentql.ts`)
  - Web scraping
  - Virtual desktop
  - Grants.gov integration

- ✅ **Credit Manager** (`lib/services/credit-manager.ts`)
  - Tier system ($10 → 10 credits, $20 → 22 credits)
  - 1.5x markup
  - Negative balance handling
  - $0 blocking

- ✅ **Stripe Service** (`lib/services/stripe.ts`)
  - Checkout sessions
  - Webhook handling
  - Refunds

- ✅ **Resend Email** (`lib/services/resend.ts`)
  - Whitelist approval emails
  - Low credit warnings
  - Grant notifications

- ✅ **R2 Storage** (`lib/services/r2-storage.ts`)
  - Document upload (50MB max)
  - Signed URLs
  - MIME validation

- ✅ **Cost Tracker** (`lib/services/cost-tracker.ts`)
  - All API usage logging
  - Cost aggregation
  - Budget monitoring

### 4. Authentication
- ✅ Auth.js v5 configuration
- ✅ Email/password provider
- ✅ JWT sessions
- ✅ RBAC (Admin/User)
- ✅ Whitelist checking

### 5. Documentation
- ✅ README.md (comprehensive)
- ✅ BUILD_PROGRESS.md
- ✅ This file (NEXT_STEPS.md)

---

## 🚧 CRITICAL NEXT STEPS (Priority Order)

### Phase 1: Get Database Running ⚡ HIGH PRIORITY

**1. Set up PostgreSQL connection**

```bash
# Option A: Use existing Heroku database
# Get DATABASE_URL from parent directory's .env
# Copy to nextjs-app/.env

# Option B: Set up local PostgreSQL
createdb smartgrantfinder
# Update DATABASE_URL in .env
```

**2. Run migrations**

```bash
cd nextjs-app
npx prisma generate
npx prisma migrate dev --name init
```

**3. Create admin user**

```bash
# We'll create a seed script for this
# Or use Prisma Studio:
npx prisma studio
```

---

### Phase 2: API Routes 🔧 HIGH PRIORITY

**Critical routes to build first:**

1. **Auth Routes** (`app/api/auth/[...nextauth]/route.ts`)
   ```typescript
   import { GET, POST } from '@/auth'
   export { GET, POST }
   ```

2. **Credit Routes** (`app/api/credits/*`)
   - `GET /api/credits/balance` - Get user balance
   - `POST /api/credits/estimate` - Estimate search cost
   - `GET /api/credits/transactions` - Transaction history

3. **Payment Routes** (`app/api/payments/*`)
   - `POST /api/payments/checkout` - Create Stripe session
   - `POST /api/webhooks/stripe` - Handle Stripe webhooks

4. **Search Routes** (`app/api/search/*`)
   - `POST /api/search/run` - Execute grant search
   - `GET /api/search/history` - Search history
   - `GET /api/search/:id/status` - Real-time status

5. **Admin Routes** (`app/api/admin/*`)
   - `GET /api/admin/users` - List pending users
   - `POST /api/admin/users/:id/whitelist` - Approve user
   - `GET /api/admin/stats` - Platform statistics

---

### Phase 3: UI Components 🎨 MEDIUM PRIORITY

**1. Install shadcn/ui**

```bash
npx shadcn@latest init
```

**2. Add base components**

```bash
npx shadcn@latest add button
npx shadcn@latest add input
npx shadcn@latest add card
npx shadcn@latest add badge
npx shadcn@latest add dialog
npx shadcn@latest add select
npx shadcn@latest add textarea
npx shadcn@latest add toast
npx shadcn@latest add dropdown-menu
npx shadcn@latest add tabs
npx shadcn@latest add separator
npx shadcn@latest add avatar
npx shadcn@latest add progress
```

**3. Custom components to build**

- `components/chat/ChatInterface.tsx` - Main chat UI
- `components/chat/MessageBubble.tsx` - Chat messages
- `components/grant/GrantCard.tsx` - Grant display card
- `components/admin/UserTable.tsx` - Admin user management
- `components/ui/CreditBadge.tsx` - Credit balance display
- `components/ui/LoadingSpinner.tsx` - Loading states

---

### Phase 4: Core Pages 📄 MEDIUM PRIORITY

**Build in this order:**

1. **Landing Page** (`app/page.tsx`)
   - Hero section
   - Pricing display
   - Sign up CTA
   - Feature highlights

2. **Auth Pages**
   - `app/auth/signin/page.tsx` - Sign in form
   - `app/auth/signup/page.tsx` - Sign up form + onboarding

3. **Main Chat** (`app/chat/page.tsx`)
   - Vercel AI SDK integration
   - Left sidebar with history
   - Settings dropdown (top-right)
   - Chat limits enforcement

4. **Admin Dashboard** (`app/admin/page.tsx`)
   - Pending users table
   - Whitelist actions
   - Platform stats

5. **Settings Page** (`app/settings/page.tsx`)
   - Cron job configuration
   - Notification preferences
   - Document uploads

---

### Phase 5: Chat Interface with Vercel AI SDK 💬 HIGH PRIORITY

**1. Install Vercel AI SDK**

Already in package.json, but verify:
```bash
npm install ai @ai-sdk/openai
```

**2. Create chat API route** (`app/api/chat/route.ts`)

```typescript
import { Configuration, OpenAIApi } from 'openai';
import { OpenAIStream, StreamingTextResponse } from 'ai';
import { DeepSeekClient } from '@/lib/services/deepseek';

export async function POST(req: Request) {
  const { messages, userId } = await req.json();

  // Check credit balance
  const canUse = await CreditManager.canUseService(userId);
  if (!canUse.allowed) {
    return new Response(canUse.reason, { status: 402 });
  }

  // Use DeepSeek for chat
  const deepseek = new DeepSeekClient();
  const response = await deepseek.chat(messages, userId);

  // Deduct credits
  await CreditManager.deductCredits(
    userId,
    response.cost,
    'Chat message'
  );

  return new Response(response.response);
}
```

**3. Build ChatInterface component**

Use `useChat` hook from Vercel AI SDK:
```typescript
import { useChat } from 'ai/react';

export function ChatInterface() {
  const { messages, input, handleInputChange, handleSubmit } = useChat({
    api: '/api/chat',
  });

  // Enforce 50 message limit
  // Render messages
  // Show grant cards in messages
}
```

---

### Phase 6: Grant Search Execution 🔍 HIGH PRIORITY

**1. Create search orchestrator** (`lib/services/grant-search.ts`)

```typescript
export class GrantSearchService {
  static async executeSearch(userId: string, query: string) {
    // 1. Check credits
    // 2. Create GrantSearch record (status: RUNNING)
    // 3. Run DeepSeek search
    // 4. Run AgentQL scraping (parallel)
    // 5. Combine + deduplicate results
    // 6. Score grants
    // 7. Store in database
    // 8. Deduct credits
    // 9. Update GrantSearch (status: COMPLETED)
    // 10. Send notification
  }
}
```

**2. Implement real-time updates**

Use Server-Sent Events (SSE) or WebSockets for live progress:
```
🔍 Starting grant search...
📡 Querying DeepSeek API... (cost: $0.0005)
✓ Found 12 potential grants
🌐 Scraping grants.gov with AgentQL...
✓ Scraped 8 new grants
🧮 Calculating relevance scores...
✓ Scored 20 grants
💾 Saving to database...
✅ Complete! Found 20 grants (8 high-priority)
Total cost: $0.047 (0.071 credits)
```

---

### Phase 7: Document Processing 📁 MEDIUM PRIORITY

**1. Create upload API** (`app/api/documents/upload/route.ts`)

```typescript
import { R2StorageService } from '@/lib/services/r2-storage';

export async function POST(req: Request) {
  const formData = await req.formData();
  const file = formData.get('file') as File;

  // Validate size (50MB max)
  // Upload to R2
  // Extract data with DeepSeek
  // Update user profile
}
```

**2. Build AI document analyzer**

Use DeepSeek to extract:
- Organization type
- Grant preferences
- Past grant history
- Budget ranges

---

### Phase 8: Cron Jobs ⏰ MEDIUM PRIORITY

**1. Create cron API** (`app/api/cron/search/route.ts`)

```typescript
export async function GET(req: Request) {
  const authHeader = req.headers.get('authorization');
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return new Response('Unauthorized', { status: 401 });
  }

  // Find users with cron enabled
  // Check current time matches their schedule
  // Execute searches (max 2/day per user)
  // Send email notifications
}
```

**2. Configure Vercel Cron** (`vercel.json`)

```json
{
  "crons": [
    {
      "path": "/api/cron/search",
      "schedule": "0 * * * *"
    }
  ]
}
```

---

### Phase 9: Testing 🧪 CRITICAL

**1. Unit tests for services**

```bash
# Test each service
npm test -- deepseek.test.ts
npm test -- credit-manager.test.ts
npm test -- agentql.test.ts
```

**2. API route tests**

```bash
npm test -- app/api/
```

**3. E2E tests**

```bash
npx playwright test
```

**Key flows to test:**
- User signup → whitelist → payment → first search
- Grant search with cost tracking
- Credit depletion → blocking → top-up
- Admin user approval workflow

---

### Phase 10: Deployment 🚀 CRITICAL

**1. Vercel setup**

```bash
npm install -g vercel
vercel login
vercel
```

**2. Environment variables**

Add all `.env` variables to Vercel dashboard:
- Database URL
- API keys (DeepSeek, AgentQL, etc.)
- Stripe keys
- Resend key
- R2 credentials

**3. Database migration**

```bash
npx prisma migrate deploy
```

**4. Create admin user in production**

```bash
npx prisma studio --browser none
# Or create via API
```

---

## 📋 File Checklist - What Still Needs Building

### API Routes (Pending)
- [ ] `app/api/auth/[...nextauth]/route.ts`
- [ ] `app/api/credits/balance/route.ts`
- [ ] `app/api/credits/estimate/route.ts`
- [ ] `app/api/payments/checkout/route.ts`
- [ ] `app/api/webhooks/stripe/route.ts`
- [ ] `app/api/search/run/route.ts`
- [ ] `app/api/admin/users/route.ts`
- [ ] `app/api/chat/route.ts`
- [ ] `app/api/documents/upload/route.ts`
- [ ] `app/api/cron/search/route.ts`

### Pages (Pending)
- [ ] `app/page.tsx` (Landing page)
- [ ] `app/auth/signin/page.tsx`
- [ ] `app/auth/signup/page.tsx`
- [ ] `app/chat/page.tsx` (MAIN APP)
- [ ] `app/admin/page.tsx`
- [ ] `app/settings/page.tsx`
- [ ] `app/layout.tsx` (Root layout)

### Components (Pending)
- [ ] `components/chat/ChatInterface.tsx`
- [ ] `components/grant/GrantCard.tsx`
- [ ] `components/admin/UserTable.tsx`
- [ ] `components/ui/CreditBadge.tsx`
- [ ] shadcn/ui base components (button, input, etc.)

### Services (Additional)
- [ ] `lib/services/grant-search.ts` (Search orchestrator)
- [ ] `lib/services/document-analyzer.ts` (AI document processing)

### Tests (Pending)
- [ ] `__tests__/services/deepseek.test.ts`
- [ ] `__tests__/services/credit-manager.test.ts`
- [ ] `__tests__/api/search.test.ts`
- [ ] `e2e/user-flow.spec.ts`

### Configuration (Pending)
- [ ] `middleware.ts` (Route protection)
- [ ] `vercel.json` (Cron configuration)
- [ ] `postcss.config.js` (Tailwind)
- [ ] `vitest.config.ts` (Test configuration)
- [ ] `playwright.config.ts` (E2E tests)

---

## 🎯 Recommended Execution Order

### Week 1: Infrastructure
1. ✅ Set up database (migrate Prisma schema)
2. ✅ Create admin user
3. Build critical API routes (auth, credits, search)
4. Install shadcn/ui

### Week 2: Core Features
5. Build chat interface (Vercel AI SDK)
6. Implement grant search execution
7. Build admin dashboard
8. Document upload system

### Week 3: Additional Features
9. Cron job system
10. Email notifications
11. Grant comparison
12. PDF export

### Week 4: Testing & Deployment
13. Write unit tests (80%+ coverage)
14. E2E tests
15. Deploy to Vercel
16. Production testing

---

## 💡 Quick Commands Reference

```bash
# Development
npm run dev                  # Start dev server
npm run build               # Build for production
npm run start               # Start production server

# Database
npx prisma studio           # Database GUI
npx prisma generate         # Generate Prisma client
npx prisma migrate dev      # Run migrations (dev)
npx prisma migrate deploy   # Run migrations (prod)

# Testing
npm test                    # Run unit tests
npm run test:e2e           # Run E2E tests
npm run test:coverage      # Coverage report

# Deployment
vercel                      # Deploy to Vercel
vercel --prod              # Deploy to production
```

---

## ❓ Common Issues & Solutions

### Issue: Prisma client not generated
**Solution:**
```bash
npx prisma generate
```

### Issue: Database connection error
**Solution:**
Check DATABASE_URL format:
```
postgresql://USER:PASSWORD@HOST:PORT/DATABASE?schema=public
```

### Issue: Auth callback error
**Solution:**
Ensure AUTH_SECRET is set and NEXTAUTH_URL matches your domain

### Issue: Stripe webhook not working
**Solution:**
1. Use Stripe CLI for local testing: `stripe listen --forward-to localhost:3000/api/webhooks/stripe`
2. Get webhook secret: `stripe listen --print-secret`

---

## 🎉 Success Criteria

Your v2.0 rebuild is complete when:

- ✅ Users can sign up and get whitelisted
- ✅ Payment processing works (Stripe)
- ✅ Credits are tracked accurately
- ✅ Chat interface is functional
- ✅ Grant searches execute successfully
- ✅ Results are stored and displayed
- ✅ Cron jobs run automatically
- ✅ Admin can manage users
- ✅ All tests pass (80%+ coverage)
- ✅ Deployed to production

---

**Current Progress**: 40% complete
**Next Milestone**: API routes + Chat interface (→ 70%)
**Final Milestone**: Testing + Deployment (→ 100%)

Good luck! 🚀
