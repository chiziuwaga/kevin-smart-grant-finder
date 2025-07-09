# Kevin's Smart Grant Finder

A comprehensive system for automatically discovering, analyzing, and prioritizing grant opportunities in telecommunications and women-owned nonprofit domains.

## Features

### 🔍 Core Discovery & Analysis

- **Automated Grant Discovery**: Searches for grants using AgentQL and Perplexity APIs
- **Smart Prioritization**: Ranks grants based on relevance to user priorities using Pinecone
- **Multi-Channel Notifications**: Telegram alerts for high-priority grants
- **Geographically Targeted**: Special focus on LA-08 district opportunities

### 💼 Bulk Operations & Data Management

- **Bulk Grant Actions**: Select multiple grants for batch save/unsave operations
- **Multi-Format Export**: Export grants to CSV, PDF, and Calendar (.ics) formats
- **Smart Filtering**: Hide expired grants toggle with date-aware filtering
- **Application Tracking**: Submit and track application feedback and outcomes

### 🎨 Modern User Interface

- **React Frontend**: Modern Material UI components with responsive design
- **Interactive Dashboard**: Grid and table views with advanced filtering
- **Real-time Updates**: Live data synchronization and progress indicators
- **Accessibility**: WCAG AA compliant with keyboard navigation support

### 🚀 Production Infrastructure

- **API Backend**: FastAPI application providing RESTful endpoints
- **Cloud Deployment**: Backend on Heroku, Frontend on Vercel
- **Robust Error Handling**: Comprehensive error boundaries and fallback mechanisms
- **Scheduled Execution**: Twice-weekly automated searches via Heroku worker

## 🆕 Latest Features (July 2025)

### Bulk Operations

- **Multi-grant selection**: Select multiple grants using checkboxes in bulk mode
- **Batch actions**: Save or unsave multiple grants at once
- **Progress indicators**: Real-time feedback during bulk operations

### Export & Integration

- **CSV Export**: Export grant data with comprehensive field coverage
- **PDF Export**: Generate formatted PDF reports via browser print dialog
- **Calendar Integration**: Export grant deadlines to .ics calendar files

### Smart Filtering

- **Hide Expired Toggle**: Filter out grants with past deadlines
- **Cross-page consistency**: Available on Dashboard, Search, and Grants pages
- **Date-aware filtering**: Automatically detects expired grants

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
   _Note: For production, this will be set in Vercel environment variables to point to your Heroku backend URL._

### Running Locally

1. Start the FastAPI backend (from project root):

   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

   _(The backend API will be available at `http://localhost:8000`)_

2. Start the React frontend (in a separate terminal):
   ```bash
   cd frontend
   npm start
   ```
   _(The frontend will be available at `http://localhost:3000`)_

### Deployment

See `frontend/DEPLOYMENT.md` for detailed instructions on deploying the backend to Heroku and the frontend to Vercel.

## Key Components

### Backend (`/` - Root Directory)

- `app/main.py`: FastAPI application entry point and service initialization.
- `app/`: Contains FastAPI routers, dependencies, schemas, and API endpoint definitions.
- `database/`: SQLAlchemy/PostgreSQL models and Pinecone client implementations.
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
