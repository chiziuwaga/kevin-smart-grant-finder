# Deployment Instructions for Smart Grant Finder

## Environment Variables

When deploying to Heroku, make sure to set the following environment variables:

### MongoDB Connection

Set the MongoDB connection using **one** of these options:

**Option 1 (Recommended):** Set the complete connection string

```
heroku config:set MONGODB_URI="mongodb+srv://kevinaitester:YOUR_PASSWORD@grantcluster.fidxu.mongodb.net/SmartGrantFinder?retryWrites=true&w=majority&appName=SmartGrantFinder"
```

**Option 2:** Set the components separately

```
heroku config:set MONGODB_USER="kevinaitester"
heroku config:set MONGODB_PASSWORD="YOUR_PASSWORD"
heroku config:set MONGODB_DBNAME="SmartGrantFinder"
```

### API Keys

```
heroku config:set PINECONE_API_KEY="your_pinecone_api_key"
heroku config:set AGENTQL_API_KEY="your_agentql_api_key"
heroku config:set PERPLEXITY_API_KEY="your_perplexity_api_key"
```

### Notification Settings

```
heroku config:set TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
```

## Deployment Commands

Deploy to Heroku with:

```
git add .
git commit -m "Update deployment configuration"
git push heroku main
```

## Kubernetes Deployment with Health Probes

We provide a Kubernetes Deployment manifest at `infrastructure/k8s/deployment.yaml` which includes both liveness and readiness probes against the `/health` endpoint:

```bash
kubectl apply -f infrastructure/k8s/deployment.yaml
```

- Ensure you replace `<your-docker-registry>/grant-finder-api:latest` in the YAML with your actual image registry path.
- The probes will start checking `/health` after the specified initial delays and mark pods as ready/unhealthy accordingly.

## Troubleshooting

If you encounter connection issues:

1. Check that environment variables are correctly set in Heroku:

   ```
   heroku config
   ```

2. View application logs:

   ```
   heroku logs --tail
   ```

3. Make sure your MongoDB Atlas network access allows connections from Heroku's IP range or allows connections from anywhere (0.0.0.0/0).

4. Verify the application can connect during a one-off dyno:
   ```
   heroku run python -c "import os; print(os.environ.get('MONGODB_URI'))"
   ```
