# Kevin's Smart Grant Finder

This project implements an automated system to find, rank, and manage grant opportunities relevant to specific domains (initially Telecommunications and Women-Owned Nonprofits), tailored for Kevin Carter.

## Features

*   **Automated Grant Scraping:** Periodically searches various sources for new grant opportunities. (Currently focuses on Louisiana grants).
*   **Relevance Ranking:** Uses Pinecone vector embeddings to score grants based on user-defined priorities.
*   **MongoDB Storage:** Stores grant details, user settings, priorities, and alert history.
*   **Streamlit Dashboard:** Provides an interactive interface to view grants, manage settings, and potentially trigger searches.
*   **Automated Alerts:** Sends notifications (SMS/Telegram) for new, high-priority grants meeting user criteria (prevents duplicate alerts within a set period).
*   **Configurable Settings:** Allows users to define relevance thresholds, deadline filters, notification preferences, and search schedules via the dashboard.
*   **Heroku Integration (Partially Simulated):** Designed for deployment on Heroku, with scheduled job execution managed via Heroku Scheduler (or Cron To Go). *Note: The automatic updating of the Heroku schedule based on user settings is currently simulated.*
*   **Mock Mode:** Supports running in mock mode for development and testing without live API calls or database connections.

## Tech Stack

*   **Backend:** Python
*   **Frontend:** Streamlit
*   **Database:** MongoDB Atlas
*   **Vector Database:** Pinecone
*   **Notifications:** Twilio (SMS), python-telegram-bot (Telegram)
*   **Scheduling:** Heroku Scheduler / Cron To Go (Recommended)
*   **Deployment:** Heroku
*   **Libraries:** `pymongo`, `pinecone-client`, `streamlit`, `python-dotenv`, `requests`, `beautifulsoup4`, `twilio`, `python-telegram-bot`, `heroku3` (for schedule management), `asyncio`

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd kevin-smart-grant-finder
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    # or
    venv\\Scripts\\activate  # Windows
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    *   Create a file named `.env` in the project root directory.
    *   Copy the contents of `.env.example` (if provided) or add the following variables, replacing placeholder values with your actual API keys and configuration:

    ```dotenv
    # --- API Keys ---
    # Pinecone
    PINECONE_API_KEY="YOUR_PINECONE_API_KEY_HERE"
    PINECONE_ENVIRONMENT="YOUR_PINECONE_ENVIRONMENT_HERE" # e.g., us-west1-gcp

    # MongoDB
    MONGODB_URI="YOUR_MONGODB_CONNECTION_STRING_HERE" # e.g., mongodb+srv://...

    # OpenAI (for Pinecone embeddings)
    OPENAI_API_KEY="YOUR_OPENAI_API_KEY_HERE"

    # Twilio (for SMS alerts)
    TWILIO_ACCOUNT_SID="YOUR_TWILIO_ACCOUNT_SID_HERE"
    TWILIO_AUTH_TOKEN="YOUR_TWILIO_AUTH_TOKEN_HERE"
    TWILIO_PHONE_NUMBER="YOUR_TWILIO_PHONE_NUMBER_HERE" # Must be Twilio number
    NOTIFY_PHONE_NUMBER="RECIPIENT_PHONE_NUMBER_HERE" # e.g., Kevin's phone number

    # Telegram (for Telegram alerts)
    TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN_HERE"
    TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID_HERE" # Can be user ID or group ID

    # Heroku (for simulated schedule updates)
    HEROKU_API_KEY="YOUR_HEROKU_API_KEY_HERE"
    HEROKU_APP_NAME="YOUR_HEROKU_APP_NAME_HERE" # Your Heroku app name

    # --- Database Config ---
    MONGODB_DATABASE="grant_finder" # Or your preferred DB name
    PINECONE_INDEX_NAME="grant-finder-index" # Or your preferred index name

    # --- Application Config ---
    # Set to "true" to use mock data and disable external API calls
    MOCK_MODE="False"
    # Set to "true" to run the scheduled job script with mock data
    SCHEDULED_JOB_MOCK_MODE="False"

    # --- Logging ---
    LOG_LEVEL="INFO" # e.g., DEBUG, INFO, WARNING, ERROR
    ```

## Running the Application

1.  **Start the Streamlit Dashboard:**
    ```bash
    streamlit run app.py
    ```
    Access the dashboard in your browser (usually at `http://localhost:8501`).

2.  **Run the Scheduled Grant Search Manually:**
    To test the grant scraping, processing, and alerting job:
    ```bash
    python utils/run_grant_search.py
    ```
    *Note: Ensure `SCHEDULED_JOB_MOCK_MODE` is set appropriately in `.env`.*

## Deployment & Scheduling (Heroku)

1.  **Deploy:** Deploy the application to Heroku using standard methods (e.g., Git push, Heroku CLI).
2.  **Configure Add-ons:**
    *   Add a MongoDB add-on (like MongoDB Atlas) or configure `MONGODB_URI` in Heroku config vars.
    *   Add a scheduler add-on like **Cron To Go** (Recommended) or **Heroku Scheduler**.
3.  **Schedule the Job:**
    Configure the scheduler add-on to run the grant search script periodically. Using Cron To Go:
    ```bash
    # Example: Run Mon & Thu at 10:00 AM America/New_York time
    heroku cron:jobs:create \
      --command "python utils/run_grant_search.py" \
      --schedule "0 14 * * 1,4" \
      --timezone "America/New_York" \
      --app YOUR_HEROKU_APP_NAME_HERE
    ```
    *(Adjust the schedule and command as needed)*

## Known Limitations

*   **Simulated Heroku Schedule Updates:** The feature allowing users to change the search schedule via the Streamlit settings page currently *simulates* the update to Heroku. It logs the intended action but does not make the actual API call to modify the Heroku Scheduler job. Implementing the real API call requires handling the Heroku Platform API directly (e.g., using `requests`).
*   **Basic Duplicate Alert Prevention:** The system prevents sending alerts for the exact same grant within a 7-day window. More sophisticated logic might be needed depending on how grants are updated or re-listed.
*   **Scraper Scope:** The current implementation primarily focuses on the Louisiana grant scraper. Expanding to other sources configured via AgentQL or Perplexity requires further development in `run_grant_search.py` or dedicated agent scripts.

## Future Enhancements

*   Implement real Heroku API calls for dynamic schedule updates.
*   Refine duplicate alert logic.
*   Expand scraper coverage and integrate AgentQL/Perplexity searches into the scheduled job.
*   Add user authentication for multi-user support.
*   Develop more sophisticated analytics and reporting.
*   Add comprehensive unit and integration tests. 