# Kevin's Smart Grant Finder

A sophisticated grant finding system using AI and multiple data sources to discover and analyze grant opportunities, with a focus on telecommunications and women-owned nonprofit domains.

## Features

- Automated grant discovery using multiple sources
- AI-powered relevance ranking using Pinecone
- Real-time updates via Streamlit dashboard
- Louisiana-specific grant scraping
- Intelligent rate limiting for API calls
- Multi-channel notifications (Email, SMS, Telegram)
- Scheduled twice-weekly updates

## Architecture

```
kevin-smart-grant-finder/
├── dashboard/           # Streamlit web interface
├── database/           # Database clients (MongoDB, Pinecone)
├── utils/
│   ├── api_handlers/   # API rate limiting and error handling
│   └── scrapers/       # Grant source scrapers
├── tests/              # Test suite
├── Dockerfile          # Container configuration
├── Procfile            # Heroku process configuration
└── requirements.txt    # Python dependencies
```

## Prerequisites

- Python 3.9+
- MongoDB Atlas account
- Pinecone account
- Heroku account
- Required API keys (see Configuration)

## Configuration

Copy `.env.example` to `.env` and configure the following:

```env
# MongoDB Configuration
MONGODB_URI=mongodb+srv://username:password@cluster0.mongodb.net/grant_finder

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENVIRONMENT=your_environment
PINECONE_INDEX_NAME=grant_priorities

# API Keys
PERPLEXITY_API_KEY=your_perplexity_api_key
OPENAI_API_KEY=your_openai_api_key

# Notification Settings
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=your_twilio_number
TELEGRAM_BOT_TOKEN=your_telegram_token
```

## Local Development

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Unix/macOS
   .\venv\Scripts\activate  # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the Streamlit dashboard:
   ```bash
   streamlit run dashboard/app.py
   ```

4. Run grant search manually:
   ```bash
   python run_grant_search.py
   ```

## Heroku Deployment

1. Install Heroku CLI and login:
   ```bash
   heroku login
   ```

2. Create Heroku app:
   ```bash
   heroku create kevin-smart-grant-finder
   ```

3. Add Cron To Go addon:
   ```bash
   heroku addons:create crontogo:basic
   ```

4. Configure environment variables:
   ```bash
   heroku config:set MONGODB_URI=your_mongodb_uri
   heroku config:set PINECONE_API_KEY=your_pinecone_api_key
   # ... set all other environment variables
   ```

5. Deploy to Heroku:
   ```bash
   git push heroku main
   ```

6. Configure scheduled jobs:
   ```bash
   heroku cron:jobs:create \
     --command "python run_grant_search.py" \
     --schedule "0 14 * * 1,4" \
     --timezone "America/New_York"
   ```

## Testing

Run the test suite:
```bash
pytest tests/
```

## Monitoring

- View Heroku logs: `heroku logs --tail`
- Monitor scheduled jobs: `heroku cron:jobs`
- Check MongoDB Atlas dashboard for database metrics
- View Pinecone dashboard for vector search performance

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details