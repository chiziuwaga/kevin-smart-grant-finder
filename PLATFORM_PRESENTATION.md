# Smart Grant Finder

## Money finder for your business while you sleep

**Prepared for:** Kevin Carter
**Prepared by:** Chizi U
**Date:** February 2026

---

## What Is This?

Smart Grant Finder is a ready-to-launch online platform that finds grants for your users automatically. It works around the clock -- searching for grants every 6 hours, scoring them for relevance, and sending email alerts when it finds strong matches. Your users sign up, enter their business details, and the system does the rest.

Think of it as a personal grant researcher that never sleeps, built for nonprofits, small businesses, and community organizations.

---

## What the Platform Does

### 1. Finds Grants Automatically

- Uses AI to build smart search strategies based on each user's business profile
- Searches across federal, state, and foundation grant databases
- Only surfaces grants with real, verified application links
- Prevents duplicate results so users never see the same grant twice

### 2. Scores Every Grant on Six Factors

Each grant gets a relevance score so users can focus on the best opportunities first:

| Factor | What It Tells the User |
| --- | --- |
| Sector Match | Does this grant fit my industry? |
| Location Match | Is this local, state, or national? (local ranks higher) |
| Organization Fit | Does my team size, revenue, and experience qualify? |
| Red Flag Check | Any disqualifying terms, ethical concerns, or org-type mismatches? |
| Feasibility | Can my organization realistically manage this grant? |
| Strategic Fit | Does this align with my stated goals? |

### 3. Writes Grant Applications

- Generates full draft applications from the user's business profile
- Covers all standard sections: Summary, Needs Statement, Project Plan, Budget, Capacity, and Impact
- Users can review, edit, and track each application

### 4. Runs on Autopilot

- Searches for new grants every 6 hours for every active user
- Sends email alerts after each search (summary + high-priority matches)
- Sends weekly digest emails with upcoming deadlines
- Warns users when they're approaching their monthly search limits

### 5. Clean, Easy-to-Use Dashboard

- Modern, professional design that works on desktop, tablet, and mobile
- Filter and sort grants by score, deadline, or status
- Save grants, track applications, and review search history
- Edit business profile with industry targeting and geographic focus

---

## How It Works (The Simple Version)

```text
 User signs up & enters business profile
              |
              v
   AI builds custom search strategy
              |
              v
   System searches grant databases every 6 hours
              |
              v
   Grants are scored & ranked for relevance
              |
              v
   User gets email alerts + sees results on dashboard
              |
              v
   User clicks "Generate Application" -> AI drafts it
```

Behind the scenes, the platform runs on reliable cloud infrastructure (hosted on Render) with a secure database, background task processing, and AI-powered analysis. Everything is deployed as a single service for simplicity.

---

## What It Costs to Run

### Hosting Costs

| Component | 100 Users | 500 Users |
| --- | --- | --- |
| Web Hosting | $7/mo | $25/mo |
| Database | $7/mo | $25/mo |
| Background Tasks | $10/mo | $10/mo |
| **Hosting Total** | **$24/mo** | **$60/mo** |

### AI Search Costs

The AI engine that powers grant discovery is extremely affordable:

| | 100 Users | 500 Users |
| --- | --- | --- |
| Searches per day | 400 | 2,000 |
| **AI Cost** | **~$15/mo** | **~$75/mo** |

### Email Costs

| Tier | Emails per Month | Cost |
| --- | --- | --- |
| Free tier | 3,000 | $0 |
| Paid tier | 50,000 | $20/mo |

### Total Monthly Operating Cost

| Scale | Hosting | AI | Email | Total |
| --- | --- | --- | --- | --- |
| **100 users** | $24 | $15 | $0 | **~$39/mo** |
| **500 users** | $60 | $75 | $20 | **~$155/mo** |

---

## Revenue Potential

At just $15/mo per user on the Basic plan:

| Scale | Monthly Revenue | Monthly Cost | Profit | Margin |
| --- | --- | --- | --- | --- |
| **100 users** | $1,500 | $39 | **$1,461** | **97%** |
| **500 users** | $7,500 | $155 | **$7,345** | **98%** |

Even a modest user base generates strong recurring revenue with extremely low operating costs.

---

## Subscription Tiers

| Feature | Trial (Free) | Basic ($15/mo) | Pro ($75/mo) |
| --- | --- | --- | --- |
| Grant Searches | 5 total | 50/month | Unlimited |
| AI-Written Applications | 0 | 20/month | Unlimited |
| Automatic Grant Monitoring | No | Yes | Yes |
| Email Alerts | Limited | Full | Full + Weekly Reports |
| Business Profiles | 1 | 1 | 3 |
| Priority Support | No | Email | Phone + Email |

---

## Turning On Payments (Stripe)

The payment system is built into the platform and ready to activate. Here is what you need to do:

1. **Create a free Stripe account** at [stripe.com](https://stripe.com)
2. **Set up two subscription products** in your Stripe dashboard:
   - Basic plan at $15/month
   - Pro plan at $75/month
3. **Copy three keys** from your Stripe dashboard into the platform settings:
   - Secret Key
   - Publishable Key
   - Webhook Secret
4. **That's it.** The platform is already wired up to handle subscriptions, payments, and billing events. Once the keys are added, billing goes live -- no code changes needed.

---

## What's Included in This Build

Here is everything that has been built and is ready to go:

- **Live, deployed web application** -- ready for users to sign up today
- **Secure login system** -- users sign in safely with industry-standard authentication
- **Full grant search engine** -- AI-powered discovery that widens its search if local results are limited
- **Smart matching** -- grants are matched to each user's profile using intelligent relevance scoring
- **Freshness tracking** -- grants older than 60 days are automatically flagged as potentially stale
- **Email notifications** -- welcome emails, search results, grant alerts, weekly reports, trial warnings, and payment failure notices
- **Professional frontend** -- clean, modern design that works on desktop, tablet, and mobile
- **"Money Finder" landing page** -- branded homepage with icons, animations, and a professional look
- **Guided onboarding** -- tooltip walkthrough that helps new users get set up (can be replayed anytime)
- **Business profile management** -- users describe their organization and the AI tailors searches to them
- **AI application writer** -- generates full grant application drafts from the user's profile
- **Automated background searches** -- the system searches for grants every 6 hours, sends daily and weekly summaries
- **Health checks** -- pre-launch script verifies the database, services, and settings are all working
- **Database migration system** -- updates to the database structure are handled automatically on deploy
- **Setup documentation** -- step-by-step instructions for anyone who needs to manage the platform

---

## Partnership & Support

This platform was designed and built by **Chizi U** with a focus on reliability, clean design, and real-world usability.

**Ongoing support is available for:**

- Bug fixes and general maintenance
- New features (additional grant sources, improved scoring, new tools)
- Stripe activation and payment testing
- Scaling guidance as your user base grows
- Custom integrations (CRM systems, accounting software, etc.)

---

*Smart Grant Finder -- Money finder for your business while you sleep.*
