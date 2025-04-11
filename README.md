# Kevin's Smart Grant Finder

A comprehensive system for automatically discovering, analyzing, and prioritizing grant opportunities in telecommunications and women-owned nonprofit domains.

## Features

- **Automated Grant Discovery**: Searches for grants using AgentQL and Perplexity APIs
- **Smart Prioritization**: Ranks grants based on relevance to user priorities using Pinecone
- **Multi-Channel Notifications**: Telegram alerts for high-priority grants
- **API Backend**: FastAPI application providing endpoints for the frontend.
- **Modern UI**: React-based frontend with Material UI and data visualizations deployed on Vercel.
- **Geographically Targeted**: Special focus on LA-08 district opportunities
- **Robust Error Handling**: Fallback mechanisms for service disruptions
- **Scheduled Execution**: Twice-weekly automated searches via Heroku worker.

## Architecture

```
+-----------------+     +-----------------+      +-----------------+
| React Frontend  | --> | FastAPI Backend | ---->| MongoDB Atlas   |
| (Vercel)        |     | (Heroku)        | <---->| (Data Storage)  |
+-----------------+     +-----------------+      +-----------------+
                           |        ^
                           |        |
                           v        |
+-----------------+     +-----------------+      +-----------------+
| External APIs   | <-- | Agents          | ---->| Pinecone        |
| (Perplexity,    |     | (Research/Rank) |      | (Vector Store)  |
| AgentQL)        |     +-----------------+      +-----------------+
+-----------------+
```

## Getting Started

### Prerequisites

- Python 3.11+ (for backend)
- Node.js 14+ (for frontend)
- MongoDB Atlas account
- Pinecone account
- Perplexity API key
- AgentQL API key
- Telegram bot token (optional)

### Backend Configuration (FastAPI on Heroku)

1. Clone the repository:
   ```bash
   git clone https://github.com/chiziuwaga/kevin-smart-grant-finder.git
   cd kevin-smart-grant-finder
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate     # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file with required credentials (see `.env.example`):
   ```
   # API Keys
   PERPLEXITY_API_KEY=...
   PINECONE_API_KEY=...
   AGENTQL_API_KEY=...
   OPENAI_API_KEY=... # Needed for Pinecone embeddings
   
   # Database
   MONGODB_URI=mongodb+srv://...
   
   # Notifications
   TELEGRAM_BOT_TOKEN=...
   ADMIN_TELEGRAM_CHAT_ID=...
   ```

### Frontend Configuration (React on Vercel)

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env` file for the frontend:
   ```
   REACT_APP_API_URL=http://localhost:8000/api # For local dev, assuming backend runs on 8000
   ```
   *Note: For production, this will be set in Vercel environment variables to point to your Heroku backend URL.* 

### Running Locally

1. Start the FastAPI backend (from project root):
   ```bash
   uvicorn Home:main_app --host 0.0.0.0 --port 8000 --reload
   ```
   *(The backend API will be available at `http://localhost:8000`)*

2. Start the React frontend (in a separate terminal):
   ```bash
   cd frontend
   npm start
   ```
   *(The frontend will be available at `http://localhost:3000`)*

### Deployment

See `frontend/DEPLOYMENT.md` for detailed instructions on deploying the backend to Heroku and the frontend to Vercel.

## Key Components

### Backend (`/` - Root Directory)

- `Home.py`: FastAPI application entry point and service initialization.
- `api/`: Contains FastAPI routers and API endpoint definitions.
- `database/`: MongoDB and Pinecone client implementations.
- `agents/`: Research and Analysis agent logic.
- `utils/`: Helper utilities, notification manager, API clients.
- `config/`: Logging configuration.
- `requirements.txt`: Backend Python dependencies.
- `Procfile`: Heroku process definitions (web and worker).
- `.env`: Backend environment variables (ignored by git).

### Frontend (`/frontend` Directory)

- `src/`: Main React application code.
  - `App.js`: Main application component with routing.
  - `components/`: Reusable UI components (Dashboard, GrantCard, Layout).
  - `api/`: Axios API client for backend communication.
  - `theme.js`: Material UI theme configuration.
- `public/`: Static assets and `index.html`.
- `package.json`: Frontend dependencies and scripts.
- `vercel.json`: Vercel deployment configuration.
- `.env`: Frontend environment variables (for local development).
- `README.md`: Frontend-specific documentation.
- `DEPLOYMENT.md`: Detailed deployment instructions for frontend and backend.

## Contributing

Please review contribution guidelines if you wish to contribute.

## License

MIT License.

## Acknowledgments

- MongoDB Atlas, Pinecone, Perplexity API, AgentQL
- FastAPI, React, Material UI
- Heroku, Vercel 