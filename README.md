# Kevin's Smart Grant Finder

A **ultra-reliable** and **error-resilient** system for automatically discovering, analyzing, and prioritizing grant opportunities in telecommunications and women-owned nonprofit domains.

## 🛡️ Why This System is Built for Grant Finding Success

**Never Miss an Opportunity:** Our graceful degradation architecture ensures the system **stays operational** even when individual services fail, so grant discovery continues uninterrupted.

**Built for Real-World Conditions:** Grant finding requires reliability in unpredictable environments - network issues, API outages, or data inconsistencies won't stop your search.

**Fail-Safe by Design:** Every component has fallback mechanisms, circuit breakers, and recovery strategies specifically designed for the critical nature of grant opportunities with time-sensitive deadlines.

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

### Search Monitoring & Alerts

- **Real-time Search Status**: Live monitoring of grant search progress with detailed status updates
- **Search Failure Alerts**: User-facing notifications for search failures with actionable recovery options
- **Comprehensive Search History**: Complete dashboard showing all manual and automated search runs
- **Automated Scheduler Monitoring**: Health status tracking for Heroku scheduled searches

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

## 🔧 Graceful Degradation System: Built for Grant Finding Reliability

### The Problem with Traditional Grant Finding Tools

Most grant discovery systems fail catastrophically when a single service goes down - losing hours of search progress, missing deadlines, or crashing entirely. Grant opportunities are time-sensitive and can't afford system downtime.

### Our Solution: Multi-Layer Fault Tolerance

#### 🏗️ **Robust Database Layer**

- **Automatic Connection Recovery**: Database connections automatically retry and recover from failures
- **Health Monitoring**: Continuous database health checks with automatic failover
- **Session Management**: Smart session handling prevents connection leaks and timeouts

#### 🛡️ **Fallback Service Architecture**

- **External API Resilience**: When Perplexity or AgentQL APIs fail, the system gracefully falls back to cached data or alternative search methods
- **Circuit Breaker Pattern**: Automatically isolates failing services to prevent cascade failures
- **Mock Service Fallbacks**: Dedicated fallback implementations ensure core functionality remains available

#### 🔄 **Smart Error Recovery**

- **Retry Mechanisms**: Intelligent retry logic with exponential backoff for transient failures
- **Graceful Degradation**: System operates in reduced capacity rather than complete failure
- **User-Friendly Error Messages**: Clear, actionable error messages instead of technical stack traces

#### 📊 **Comprehensive Health Monitoring**

- **Real-time Status**: Live monitoring of all system components and external services
- **Proactive Alerts**: Early warning system for potential issues before they impact users
- **Detailed Diagnostics**: Complete system health reports for rapid troubleshooting

### Why This Matters for Grant Finding

**🎯 Never Miss a Deadline**: System reliability ensures grant searches complete even during API outages or network issues.

**📈 Consistent Performance**: Fallback mechanisms maintain search quality when primary services are unavailable.

**⚡ Rapid Recovery**: Automatic recovery strategies minimize downtime and keep grant discovery running.

**🔍 Transparent Operations**: Clear status reporting helps users understand system state and take appropriate action.

## Architecture: Fault-Tolerant Grant Finding System

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

### 🔧 New Graceful Degradation Components

- **`app_graceful.py`**: Enhanced FastAPI application with comprehensive error handling and fallback mechanisms
- **`fixes/database/`**: Robust database connection management with automatic retry and health monitoring
- **`fixes/services/`**: Fallback service implementations and circuit breaker patterns
- **`fixes/models/`**: Safe model conversion utilities preventing AttributeError crashes
- **`fixes/error_handling/`**: Global error handlers and recovery strategies
- **`fixes/monitoring/`**: Real-time health monitoring and diagnostic endpoints

### 🚀 Reliability Features

- **Zero-Downtime Fallbacks**: System continues operating even when external APIs fail
- **Intelligent Retry Logic**: Automatic recovery from transient failures
- **Health Monitoring**: Real-time status of all system components
- **Safe Model Handling**: Null-safe operations preventing data conversion errors
- **Circuit Breaker Protection**: Automatic isolation of failing services

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

### Running the Graceful System (Recommended)

For maximum reliability, use the new graceful degradation system:

1. **Start with Graceful Backend:**

   ```bash
   uvicorn app_graceful:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Health Check the System:**

   ```bash
   curl http://localhost:8000/health/system
   ```

3. **Monitor Service Status:**
   ```bash
   curl http://localhost:8000/health/services
   ```

The graceful system provides:

- **Automatic failover** when external APIs are down
- **Comprehensive error recovery** for database issues
- **Real-time health monitoring** of all components
- **Fallback mechanisms** ensuring core functionality remains available

### Deployment

See `frontend/DEPLOYMENT.md` for detailed instructions on deploying the backend to Heroku and the frontend to Vercel.

## Key Components: Reliable Grant Finding Infrastructure

### Backend (Root Directory)

#### 🔧 **Graceful Degradation System** (Recommended)

- **`app_graceful.py`**: Enhanced FastAPI application with comprehensive error handling and fallback mechanisms
- **`fixes/database/`**: Robust database connection management with automatic retry and health monitoring
- **`fixes/services/`**: Fallback service implementations and circuit breaker patterns for external APIs
- **`fixes/models/`**: Safe model conversion utilities preventing AttributeError crashes
- **`fixes/error_handling/`**: Global error handlers and recovery strategies
- **`fixes/monitoring/`**: Real-time health monitoring and diagnostic endpoints

#### 🏗️ **Core Application**

- **`app/main.py`**: Original FastAPI application entry point and service initialization
- **`app/`**: FastAPI routers, dependencies, schemas, and API endpoint definitions
- **`database/`**: SQLAlchemy/PostgreSQL models and Pinecone client implementations
- **`agents/`**: Research and Analysis agent logic for grant discovery
- **`utils/`**: Helper utilities, notification manager, API clients
- **`config/`**: System configuration and logging setup

#### 📋 **Dependencies & Deployment**

- **`requirements.txt`**: Backend Python dependencies
- **`Procfile`**: Heroku process definitions (web and worker)
- **`deploy_graceful_system.py`**: Automated deployment script for the graceful system
- **`.env`**: Backend environment variables (ignored by git)

### Frontend (`/frontend` Directory)

- **`src/`**: Main React application code
  - **`App.js`**: Main application component with routing
  - **`components/`**: Reusable UI components (Dashboard, GrantCard, Layout)
  - **`api/`**: Axios API client for backend communication
  - **`theme.js`**: Material UI theme configuration
- **`public/`**: Static assets and `index.html`
- **`package.json`**: Frontend dependencies and scripts
- **`vercel.json`**: Vercel deployment configuration
- **`.env`**: Frontend environment variables (for local development)

### 📚 **Documentation & Testing**

#### 🔍 **System Documentation**

- **`GRACEFUL_DEGRADATION_README.md`**: Complete guide to the graceful degradation system
- **`SYSTEM_ARCHITECTURE.md`**: Detailed system architecture and component relationships
- **`IMPLEMENTATION_SUMMARY.md`**: Summary of all graceful degradation improvements

#### 📚 **Additional Documentation**

- **[Grant Finding Reliability Benefits](GRANT_FINDING_RELIABILITY_BENEFITS.md)**: Detailed explanation of how the graceful degradation system addresses grant finding challenges
- **[Graceful Degradation Technical Guide](GRACEFUL_DEGRADATION_README.md)**: Complete technical implementation guide
- **[System Architecture Overview](SYSTEM_ARCHITECTURE.md)**: Comprehensive system design and component relationships
- **[Implementation Summary](IMPLEMENTATION_SUMMARY.md)**: Current status and completed improvements

#### 🧪 **Comprehensive Testing**

- **`test_graceful_system.py`**: Complete test suite for all graceful degradation features
- **`tests/`**: Original test suite for core functionality
- **Health Monitoring Tests**: Automated validation of fallback mechanisms and error recovery

#### 📖 **Legacy Documentation**

- **`frontend/README.md`**: Frontend-specific documentation
- **`frontend/DEPLOYMENT.md`**: Detailed deployment instructions for frontend and backend

## 🚀 Get Started with Ultra-Reliable Grant Finding

### Quick Start (Recommended Path)

1. **Clone and Setup:**

   ```bash
   git clone https://github.com/chiziuwaga/kevin-smart-grant-finder.git
   cd kevin-smart-grant-finder
   ```

2. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment:**

   - Copy `.env.example` to `.env`
   - Add your API keys (Perplexity, AgentQL, OpenAI, etc.)

4. **Start the Graceful System:**

   ```bash
   uvicorn app_graceful:app --host 0.0.0.0 --port 8000 --reload
   ```

5. **Verify Health:**
   ```bash
   curl http://localhost:8000/health/system
   ```

### Why This Approach Works Better

- **🎯 Grant-Focused Design**: Every component is optimized for the time-sensitive nature of grant opportunities
- **🛡️ Failure-Resistant**: Multiple layers of protection ensure you never miss opportunities due to technical issues
- **📊 Transparent Operations**: Real-time monitoring helps you understand exactly what's happening with your searches
- **⚡ Rapid Recovery**: Automatic retry and fallback mechanisms minimize disruption to your grant finding workflow

## 📋 Production Deployment

The graceful degradation system is production-ready and includes:

- **Automated deployment scripts** (`deploy_graceful_system.py`)
- **Health monitoring endpoints** for production monitoring
- **Comprehensive error logging** for troubleshooting
- **Fallback mechanisms** for high availability

## Contributing

Please review contribution guidelines if you wish to contribute.

## License

MIT License.

## Acknowledgments

- MongoDB Atlas, Pinecone, Perplexity API, AgentQL
- FastAPI, React, Material UI
- Heroku, Vercel
