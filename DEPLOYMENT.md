# Deployment Guide

## Heroku Deployment

### Prerequisites

1. Heroku account and Heroku CLI installed
2. MongoDB Atlas cluster
3. Pinecone account and index
4. Required API keys

### Step-by-Step Deployment

1. **Login to Heroku**
   ```bash
   heroku login
   ```

2. **Create Heroku Application**
   ```bash
   heroku create kevin-smart-grant-finder
   ```

3. **Add Required Buildpacks**
   ```bash
   heroku buildpacks:set heroku/python
   ```

4. **Configure Environment Variables**
   ```bash
   # Database configuration
   heroku config:set MONGODB_URI="your_mongodb_uri"
   
   # Pinecone configuration
   heroku config:set PINECONE_API_KEY="your_pinecone_api_key"
   heroku config:set PINECONE_ENVIRONMENT="your_environment"
   heroku config:set PINECONE_INDEX_NAME="grant_priorities"
   
   # API keys
   heroku config:set PERPLEXITY_API_KEY="your_perplexity_api_key"
   heroku config:set OPENAI_API_KEY="your_openai_api_key"
   
   # Notification settings
   heroku config:set TWILIO_ACCOUNT_SID="your_twilio_sid"
   heroku config:set TWILIO_AUTH_TOKEN="your_twilio_token"
   heroku config:set TWILIO_PHONE_NUMBER="your_twilio_number"
   heroku config:set TELEGRAM_BOT_TOKEN="your_telegram_token"
   ```

5. **Add Cron To Go Add-on**
   ```bash
   heroku addons:create crontogo:basic
   ```

6. **Configure Scheduled Jobs**
   ```bash
   # Create Monday/Thursday 10 AM ET jobs
   heroku cron:jobs:create \
     --command "python run_grant_search.py" \
     --schedule "0 14 * * 1,4" \
     --timezone "America/New_York" \
     --app kevin-grant-finder
   ```

7. **Deploy Application**
   ```bash
   git push heroku main
   ```

8. **Scale Dynos**
   ```bash
   heroku ps:scale web=1
   ```

9. **Verify Deployment**
   ```bash
   heroku open
   ```

### Monitoring and Maintenance

1. **View Application Logs**
   ```bash
   heroku logs --tail
   ```

2. **Monitor Scheduled Jobs**
   ```bash
   heroku cron:jobs
   heroku cron:jobs:logs
   ```

3. **Check Application Status**
   ```bash
   heroku ps
   ```

4. **Update Configuration**
   ```bash
   heroku config:set KEY=VALUE
   ```

### Troubleshooting

1. **Job Execution Issues**
   - Check job logs: `heroku cron:jobs:logs`
   - Verify environment variables: `heroku config`
   - Ensure worker dyno is running: `heroku ps`

2. **Database Connection Issues**
   - Verify MongoDB URI: `heroku config:get MONGODB_URI`
   - Check MongoDB Atlas status
   - Review application logs: `heroku logs --tail`

3. **API Rate Limiting**
   - Monitor Perplexity API usage in logs
   - Check rate limit handler logs
   - Adjust batch sizes if needed

### Backup and Recovery

1. **Database Backup**
   - Enable MongoDB Atlas continuous backup
   - Schedule regular snapshots

2. **Configuration Backup**
   ```bash
   heroku config -s > .env.backup
   ```

3. **Application Rollback**
   ```bash
   heroku releases
   heroku rollback v<version>
   ```

### Security Considerations

1. **Environment Variables**
   - Use secure values for all API keys
   - Regularly rotate sensitive credentials
   - Monitor for unauthorized access

2. **Access Control**
   - Limit Heroku dashboard access
   - Use two-factor authentication
   - Review deployment logs regularly

3. **Data Protection**
   - Enable MongoDB Atlas encryption
   - Use secure HTTPS connections
   - Implement rate limiting

### Performance Optimization

1. **Database Optimization**
   - Create necessary indexes
   - Monitor query performance
   - Optimize connection pooling

2. **Application Settings**
   - Adjust dyno sizes as needed
   - Configure memory limits
   - Optimize worker processes

3. **Caching Strategy**
   - Implement result caching
   - Use Redis if needed
   - Monitor cache hit rates