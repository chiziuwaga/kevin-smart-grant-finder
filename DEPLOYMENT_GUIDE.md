# Deployment Guide - Kevin Smart Grant Finder

## Pre-Deployment Checklist ✅

### Environment Configuration
- [x] All API keys configured in `.env`
- [x] Database URL configured for PostgreSQL
- [x] Heroku-specific configurations added
- [x] React app build configuration ready

### Code Quality
- [x] Backend syntax errors fixed
- [x] Frontend compiles successfully
- [x] All dependencies properly listed
- [x] Health check endpoint functional

## GitHub Deployment Steps

### 1. Initialize Git Repository (if not done)
```bash
git init
git remote add origin https://github.com/yourusername/kevin-smart-grant-finder.git
```

### 2. Prepare for GitHub Push
```bash
# Add all files
git add .

# Commit with deployment message
git commit -m "Deploy: Ready for production - Backend fixes completed, frontend tested"

# Push to main branch
git push origin main
```

### 3. Set Branch to Main (GitHub Default)
- GitHub will automatically use `main` as the default branch
- No additional configuration needed

## Heroku Deployment Steps

### 1. Heroku App Configuration
Your app name: `smartgrantfinder`
- App is already configured in `.env`
- Heroku API key is present

### 2. Environment Variables to Set in Heroku
Copy these from your `.env` file to Heroku Config Vars:

```bash
# Database (should auto-configure)
DATABASE_URL=postgresql+asyncpg://...

# API Keys
PERPLEXITY_API_KEY=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
OPENAI_API_KEY=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
PINECONE_API_KEY=pcsk_2a2RC5_LQjvSf1cjgXbD5EnwNcQRAL6naCx7KTLcBvD2QAYuCPJjNiEELFksdCqgx8apUB
PINECONE_INDEX_NAME=grantcluster
PINECONE_REGION=us-east-1
PINECONE_CLOUD=aws

# Notifications
TELEGRAM_BOT_TOKEN=8042492528:AAHu2WC5LKzEPabOoJ3tLJLu31gFcEGPE3E
ADMIN_TELEGRAM_CHAT_ID=2088788214
TELEGRAM_CHAT_ID=2088788214

# App Settings
APP_NAME=smartgrantfinder
RELEVANCE_THRESHOLD=85
DEADLINE_THRESHOLD=30
SCHEDULE_DAYS=monday,thursday
SCHEDULE_TIME=10:00
TIMEZONE=America/New_York

# Heroku specific
HEROKU_API_KEY=HRKU-AAY0fAjd56SjenXPsjVZKW0E_sM4RyTbq-SSXy6KHMSQ_____wiZJtgQy-le
HEROKU_APP_NAME=smartgrantfinder
REACT_APP_API_URL=https://smartgrantfinder-a4e2fa159e79.herokuapp.com/api
```

### 3. Manual Deployment via Heroku Dashboard
1. Go to https://dashboard.heroku.com/apps/smartgrantfinder
2. Navigate to "Deploy" tab
3. Connect to your GitHub repository
4. Enable automatic deploys from `main` branch
5. Click "Deploy Branch" for manual deployment

### 4. Alternative: Heroku CLI Deployment
```bash
# Login to Heroku
heroku login

# Set remote
heroku git:remote -a smartgrantfinder

# Deploy
git push heroku main
```

## Post-Deployment Verification

### 1. Backend Health Check
Visit: `https://smartgrantfinder-a4e2fa159e79.herokuapp.com/health`

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-06-05T...",
  "version": "1.0.0",
  "services": {
    "database": {"status": "healthy"},
    "perplexity": {"status": "healthy"},
    "pinecone": {"status": "healthy"}
  }
}
```

### 2. Frontend Access
Visit: `https://smartgrantfinder-a4e2fa159e79.herokuapp.com`
- Should show login screen
- Authentication: password "smartgrantfinder"

### 3. API Endpoints Test
- `/api/grants/search` - Grant search functionality
- `/api/grants/saved` - Saved grants management
- `/api/settings` - App configuration

## File Structure for Deployment

### Critical Files Present ✅
- `Procfile` - Heroku process definition
- `requirements.txt` - Python dependencies
- `runtime.txt` - Python version specification
- `app.json` - Heroku app metadata
- `heroku.yml` - Container deployment config
- `package.json` - Frontend dependencies

### Deployment Configuration Files
- `frontend/vercel.json` - Frontend deployment config
- `frontend/deploy.sh` - Deployment script
- `infrastructure/k8s/deployment.yaml` - Kubernetes config (optional)

## Troubleshooting

### Common Issues
1. **Database Connection**: Ensure SSL parameters are correct
2. **API Keys**: Verify all keys are set in Heroku config vars
3. **Build Failures**: Check `requirements.txt` and `package.json`
4. **CORS Issues**: Frontend URL may need adjustment

### Logs Access
```bash
# View Heroku logs
heroku logs --tail -a smartgrantfinder

# View specific dyno logs
heroku logs --dyno web -a smartgrantfinder
```

## Success Criteria ✅

- [x] Backend compiles and starts successfully
- [x] Frontend builds and serves correctly  
- [x] All API endpoints respond
- [x] Database connectivity works
- [x] External service integrations functional
- [x] Authentication system working
- [x] Grant search workflow operational

## Ready for Deployment! 🚀

Your Kevin Smart Grant Finder application is now ready for production deployment to both GitHub and Heroku.
