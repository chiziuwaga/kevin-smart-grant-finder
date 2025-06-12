# Kevin's Smart Grant Finder - VS Code Workspace Instructions

## 🚀 Project Overview

**Advanced Grant Finder & Analysis System** - A sophisticated AI-powered platform for discovering, analyzing, and managing grant opportunities with advanced scoring algorithms and compliance validation.

## 🔗 Live System URLs

- **Frontend Application**: https://smartgrantfinder.vercel.app/
- **Backend API**: https://smartgrantfinder-a4e2fa159e79.herokuapp.com/
- **API Documentation**: https://smartgrantfinder-a4e2fa159e79.herokuapp.com/api/docs
- **Health Check**: https://smartgrantfinder-a4e2fa159e79.herokuapp.com/health

## 🏗️ Project Structure

```
📁 kevin-smart-grant-finder/          # Root project directory
├── 📂 app/                           # FastAPI Backend Application
│   ├── main.py                       # Application entry point & service initialization
│   ├── router.py                     # API endpoints & route definitions
│   ├── crud.py                       # Database CRUD operations
│   ├── schemas.py                    # Pydantic models for API contracts
│   ├── dependencies.py               # Dependency injection & shared services
│   └── services.py                   # Service layer initialization
├── 📂 agents/                        # AI Agent System
│   ├── research_agent.py             # Grant discovery & initial scoring
│   ├── compliance_agent.py           # Business logic & feasibility validation
│   └── analysis_agent.py             # Advanced grant analysis
├── 📂 database/                      # Data Persistence Layer
│   ├── models.py                     # SQLAlchemy database models
│   └── session.py                    # Database connection & session management
├── 📂 config/                        # Configuration Management
│   ├── settings.py                   # Application settings & environment variables
│   ├── kevin_profile_config.yaml     # User/business profile configuration
│   ├── compliance_rules_config.yaml  # Business validation rules
│   ├── sector_config.yaml            # Industry sector classifications
│   └── geographic_config.yaml        # Geographic preferences & targeting
├── 📂 frontend/                      # React Frontend Application
│   ├── src/components/               # React UI components
│   ├── src/api/                      # API integration layer
│   ├── package.json                  # Frontend dependencies
│   └── vercel.json                   # Vercel deployment configuration
├── 📂 tests/                         # Comprehensive Test Suite
│   ├── test_agents.py                # AI agent testing
│   ├── test_api.py                   # API endpoint testing
│   ├── test_crud_enriched.py         # Database operations testing
│   └── conftest.py                   # Test configuration & fixtures
├── 📂 utils/                         # Utility Functions & Clients
│   ├── perplexity_client.py          # Perplexity AI service client
│   ├── pinecone_client.py            # Pinecone vector database client
│   └── notification_manager.py       # Alert & notification system
└── 📂 docs/                          # Project Documentation
    ├── EXECUTION_PLAN.md             # Development roadmap & milestones
    ├── UAT_TESTING_GUIDE.md          # User acceptance testing protocols
    └── DEPLOYMENT_GUIDE.md           # Production deployment instructions
```

## ⚡ Quick Development Commands

### 🐍 Backend Development
```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/ -v

# Run specific test files
pytest tests/test_agents.py -v
pytest tests/test_api.py -v

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "Description"

# Check database connection
python test_db.py

# Test all services
python test_services.py
```

### ⚛️ Frontend Development
```powershell
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build

# Deploy to Vercel
npm run deploy
```

### 🧪 Testing & Quality Assurance
```powershell
# Run full test suite
pytest tests/ -v --cov=app --cov=agents --cov=utils

# Run integration tests
python tests/integration_test_simple.py

# Test production API
python tests/production_api_test.py

# Lint Python code
flake8 app/ agents/ utils/

# Format Python code
black app/ agents/ utils/
```

## 🔧 Development Environment Setup

### 1. Prerequisites Check
```powershell
# Verify Python version (3.11+ required)
python --version

# Verify Node.js version (18+ required)
node --version

# Verify Git configuration
git config --list
```

### 2. Environment Configuration
```powershell
# Copy environment template
cp .env.example .env

# Required environment variables:
# PERPLEXITY_API_KEY=your_perplexity_key
# PINECONE_API_KEY=your_pinecone_key
# OPENAI_API_KEY=your_openai_key
# DATABASE_URL=postgresql://user:pass@localhost/dbname
# TELEGRAM_BOT_TOKEN=your_telegram_token (optional)
```

### 3. Database Setup
```powershell
# Initialize PostgreSQL database
# Install PostgreSQL locally or use cloud provider

# Run initial migrations
alembic upgrade head

# Verify database connection
python test_db.py
```

## 🎯 Key Development Areas

### 🤖 AI Agents (`/agents/`)
- **ResearchAgent**: Handles grant discovery using multi-tier search strategies
- **ComplianceAgent**: Validates grants against business rules and feasibility
- **AnalysisAgent**: Performs advanced analysis and prioritization

### 🗄️ Database Layer (`/database/`)
- **Models**: SQLAlchemy models for grants, analysis, search runs, user settings
- **Session**: Database connection and session management
- **Migrations**: Alembic migration files for schema changes

### 🌐 API Layer (`/app/`)
- **Router**: RESTful API endpoints for frontend integration
- **CRUD**: Database operations and business logic
- **Schemas**: Pydantic models for request/response validation
- **Dependencies**: Shared services and dependency injection

### ⚙️ Configuration (`/config/`)
- **Settings**: Environment-based configuration management
- **YAML Configs**: Business rules, user profiles, sector definitions
- **Logging**: Centralized logging configuration

## 🚨 Important Files to Monitor

### 🔴 Critical Configuration Files
- `.env` - Environment variables (never commit to git)
- `requirements.txt` - Python dependencies
- `alembic.ini` - Database migration configuration
- `Procfile` - Heroku deployment processes

### 🟡 Business Logic Files
- `config/kevin_profile_config.yaml` - User business profile
- `config/compliance_rules_config.yaml` - Validation rules
- `config/sector_config.yaml` - Industry classifications

### 🟢 Deployment Files
- `heroku.yml` - Heroku container deployment
- `frontend/vercel.json` - Vercel deployment configuration
- `runtime.txt` - Python runtime specification

## 🐛 Common Development Issues & Solutions

### Database Connection Issues
```powershell
# Check database status
python test_db.py

# Reset database connection
# Restart PostgreSQL service
# Verify DATABASE_URL in .env

# Run fresh migrations
alembic downgrade base
alembic upgrade head
```

### API Service Issues
```powershell
# Test individual services
python test_services.py

# Check service initialization
python -c "from app.services import init_services; import asyncio; asyncio.run(init_services())"

# Verify API keys in .env file
```

### Frontend Build Issues
```powershell
cd frontend

# Clear node modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Check environment variables
cat .env

# Rebuild from scratch
npm run build
```

## 📊 Performance Monitoring

### Backend Health Checks
```powershell
# Local health check
curl http://localhost:8000/health

# Production health check
curl https://smartgrantfinder-a4e2fa159e79.herokuapp.com/health

# Database performance test
python -c "import time; from database.session import test_connection; start=time.time(); test_connection(); print(f'DB Connection: {time.time()-start:.2f}s')"
```

### Frontend Performance
```powershell
cd frontend

# Analyze bundle size
npm run build
npm run analyze

# Check lighthouse scores
npx lighthouse https://smartgrantfinder.vercel.app/
```

## 🔄 Git Workflow

### Branch Management
```powershell
# Create feature branch
git checkout -b feature/new-feature-name

# Switch between branches
git checkout main
git checkout develop

# Update branch with latest changes
git pull origin main
git merge main
```

### Deployment Process
```powershell
# Push to trigger deployments
git push origin main  # Triggers both Heroku and Vercel deployments

# Check deployment status
# Heroku: https://dashboard.heroku.com/apps/smartgrantfinder
# Vercel: https://vercel.com/dashboard
```

## 📱 VS Code Extensions Recommended

- **Python** - Python language support
- **Pylance** - Enhanced Python IntelliSense
- **Python Docstring Generator** - Auto-generate docstrings
- **Thunder Client** - API testing within VS Code
- **ES7+ React/Redux/React-Native snippets** - React development
- **Prettier** - Code formatting
- **GitLens** - Enhanced Git capabilities
- **Docker** - Container support
- **PostgreSQL** - Database management

## 🎯 Development Tips

### Efficient Development Workflow
1. **Always activate virtual environment** before backend development
2. **Run tests frequently** - `pytest tests/ -v`
3. **Use hot reload** - Both backend (`--reload`) and frontend (`npm start`) support it
4. **Monitor logs** - Check both console output and log files
5. **Test API endpoints** - Use `/api/docs` for interactive testing

### Code Quality
- **Follow PEP 8** for Python code style
- **Use type hints** in Python functions
- **Write comprehensive docstrings** for functions and classes
- **Maintain test coverage** above 80%
- **Update documentation** when adding features

### Debugging
- **Use VS Code debugger** for step-through debugging
- **Check log files** in `/logs/` directory
- **Use print statements** strategically in development
- **Test individual components** in isolation
- **Monitor database queries** using SQLAlchemy logging

---

**Happy Coding! 🚀**

*Last Updated: June 12, 2025*
*System Status: Production Ready ✅*