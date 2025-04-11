# Deployment Guide for Smart Grant Finder

This guide provides instructions for deploying both the backend and frontend components of the Smart Grant Finder application.

## Backend (Heroku)

The backend is a Streamlit application that provides the API for the frontend.

### Prerequisites

- Heroku CLI installed
- Git
- Python 3.11+
- MongoDB Atlas account
- Pinecone account and API key

### Deployment Steps

1. **Set up environment variables in Heroku**

   ```bash
   # MongoDB connection
   heroku config:set MONGODB_URI="mongodb+srv://kevinaitester:YOUR_PASSWORD@grantcluster.fidxu.mongodb.net/SmartGrantFinder?retryWrites=true&w=majority"
   
   # API keys
   heroku config:set PINECONE_API_KEY="your_pinecone_api_key"
   heroku config:set AGENTQL_API_KEY="your_agentql_api_key"  
   heroku config:set PERPLEXITY_API_KEY="your_perplexity_api_key"
   
   # Notification settings (optional)
   heroku config:set TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
   ```

2. **Deploy backend to Heroku**

   ```bash
   git push heroku main
   ```

3. **Verify backend deployment**

   Visit your Heroku app URL to make sure the application is running:
   
   ```bash
   heroku open
   ```
   
   The API endpoints should be available at: `https://your-app-name.herokuapp.com/api/`

## Frontend (Vercel)

The frontend is a React application that connects to the backend API.

### Prerequisites

- Node.js and npm installed
- Vercel CLI installed
- Git

### Deployment Steps

1. **Build frontend for production**

   ```bash
   cd frontend
   npm install
   npm run build
   ```

2. **Deploy to Vercel**

   ```bash
   # Login to Vercel if you haven't already
   vercel login
   
   # Deploy
   vercel --prod
   ```

3. **Environment Variables**

   Set the following environment variables in the Vercel dashboard:
   
   - `REACT_APP_API_URL`: URL of your Heroku backend's API (e.g., `https://kevin-smart-grant-finder.herokuapp.com/api`)

4. **Verification**

   Visit your deployed Vercel URL to ensure the frontend is connecting properly to the backend.

## Post-Deployment Checks

1. **API Connectivity**

   Verify that the frontend can connect to the backend API:
   
   ```bash
   curl https://your-heroku-app.herokuapp.com/api/system/status
   ```

2. **MongoDB Connection**

   Check if the backend is connecting to MongoDB:
   
   ```bash
   heroku logs --tail
   ```
   
   Look for successful MongoDB connection messages.

3. **Frontend-Backend Integration**

   Login to the frontend and verify that data is loading correctly from the backend.

## Troubleshooting

### Backend Issues

- **MongoDB Connection Errors**
  
  Check the MongoDB URI format in environment variables and ensure MongoDB Atlas network access settings allow connections from Heroku.

- **API Errors**
  
  Review the Heroku logs for any API-related errors:
  
  ```bash
  heroku logs --tail
  ```

### Frontend Issues

- **API Connection Errors**
  
  Ensure the correct API URL is set in the Vercel environment variables.

- **Blank Pages or Loading Issues**
  
  Check browser console for JavaScript errors and verify that build files are properly generated.

## Updating the Application

### Backend Updates

1. Make your changes
2. Commit and push to Heroku:
   ```bash
   git add .
   git commit -m "Update description"
   git push heroku main
   ```

### Frontend Updates

1. Make changes to the frontend code
2. Build and redeploy:
   ```bash
   cd frontend
   npm run build
   vercel --prod
   ``` 