# Kevin's Smart Grant Finder

A specialized grant search system that automatically finds and tracks relevant grants for telecommunications and women-owned nonprofits, with a focus on the LA-08 region.

## Features

- 🔍 Automated grant searching twice weekly (Monday and Thursday)
- 📊 Smart relevance scoring using Pinecone vector similarity
- 🔔 Notifications via SMS and Telegram
- 📱 Modern Streamlit dashboard interface
- 🤖 Direct scraping of government grant sources
- 💾 Persistent storage with MongoDB Atlas

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/kevin-smart-grant-finder.git
   cd kevin-smart-grant-finder
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and add your API keys and configuration:
   - Perplexity API key
   - Pinecone API key and environment
   - OpenAI API key
   - MongoDB connection string
   - Twilio credentials (optional)
   - Telegram bot token (optional)

5. **Initialize MongoDB Collections**
   The system will automatically create these collections on first run:
   - `grants`: Stores grant information
   - `priorities`: Stores search priorities
   - `search_history`: Tracks search operations
   - `saved_grants`: User-saved grants

6. **Run the Application**
   ```bash
   streamlit run app.py
   ```

## Project Structure

```
kevin-smart-grant-finder/
├── app.py                  # Main Streamlit application
├── requirements.txt        # Python dependencies
├── .env                   # Environment variables
├── agents/                # Agent implementations
├── database/             # Database connectors
│   ├── mongodb_client.py
│   └── pinecone_client.py
├── scrapers/             # Web scrapers
│   └── grant_scraper.py
├── utils/                # Utility functions
│   ├── notification_manager.py
│   └── scheduler.py
└── tests/               # Test suite
```

## Usage

1. **Dashboard**
   - View high-priority grants
   - Track approaching deadlines
   - Monitor total available funding

2. **Search Grants**
   - Filter by category (Telecommunications/Women-Owned Nonprofit)
   - Set funding type and eligibility criteria
   - Save interesting grants

3. **Analytics**
   - View grant distribution by category
   - Track funding trends
   - Monitor search performance

4. **Settings**
   - Configure notification preferences
   - Set search schedule
   - Adjust relevance thresholds

## Automated Searches

The system performs automated searches twice weekly:
- Every Monday and Thursday at 10:00 AM (configurable)
- Searches government sources directly (Grants.gov, USDA, etc.)
- Calculates relevance scores using Pinecone
- Sends notifications for high-priority matches

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 