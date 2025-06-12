# Kevin's Advanced Grant Finder & Analysis System

A sophisticated AI-powered platform for discovering, analyzing, and managing grant opportunities with advanced scoring algorithms, compliance validation, and intelligent prioritization.

## 🚀 System Overview

**Live Application URLs:**
- **Frontend:** https://smartgrantfinder.vercel.app/
- **Backend API:** https://smartgrantfinder-a4e2fa159e79.herokuapp.com/
- **API Documentation:** https://smartgrantfinder-a4e2fa159e79.herokuapp.com/api/docs
- **Health Check:** https://smartgrantfinder-a4e2fa159e79.herokuapp.com/health

## ✨ Advanced Features

### 🔍 **Intelligent Grant Discovery**
- **Multi-Tier Search Strategy**: Sophisticated search algorithms using Perplexity AI
- **LLM-Enhanced Data Extraction**: Automatic grant summarization and categorization
- **Sector-Specific Targeting**: Focus on technology, telecommunications, and community development
- **Geographic Intelligence**: Louisiana-specific prioritization with national scope

### 🧠 **Advanced AI Scoring System**
- **Research Context Analysis**: 
  - Sector relevance scoring (0.0-1.0)
  - Geographic alignment assessment
  - Operational capacity matching
- **Compliance Validation**:
  - Business logic alignment checks
  - Feasibility assessment based on organizational capacity
  - Strategic synergy evaluation
- **Composite Scoring**: Weighted final scores for intelligent prioritization

### 📊 **Comprehensive Grant Management**
- **Enriched Grant Profiles**: Complete grant information with AI-generated insights
- **Application Tracking**: Full lifecycle management from discovery to outcome
- **Historical Analysis**: Performance tracking and outcome optimization
- **Smart Notifications**: Intelligent alerts based on priority and deadlines

### 🔧 **Enterprise-Grade Architecture**
- **Production-Ready Deployment**: Heroku backend + Vercel frontend
- **PostgreSQL Database**: Robust data persistence with SQLAlchemy ORM
- **Vector Search**: Pinecone integration for semantic grant matching
- **API-First Design**: RESTful endpoints with comprehensive documentation
- **Automated Testing**: Comprehensive test suite including UAT protocols

## 🏗️ System Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  React Frontend │────▶│ FastAPI Backend │────▶│  PostgreSQL DB  │
│    (Vercel)     │     │    (Heroku)     │     │   (Heroku)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │         ▲
                               │         │
                               ▼         │
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   AI Services   │◀────│   Agent System  │────▶│  Pinecone VDB   │
│ (Perplexity AI) │     │ Research/Comply │     │ (Vector Store)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │  Notifications  │
                        │   (Telegram)    │
                        └─────────────────┘
```

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI with async/await support
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI Integration**: Perplexity API for LLM capabilities
- **Vector Search**: Pinecone for semantic matching
- **Deployment**: Heroku with worker processes
- **Testing**: Pytest with comprehensive coverage

### Frontend
- **Framework**: React 18 with TypeScript
- **UI Library**: Material-UI (MUI) v5
- **State Management**: React hooks and context
- **Charts**: Recharts for data visualization
- **Deployment**: Vercel with automatic deployments
- **Authentication**: Password-protected interface

### AI & ML Components
- **Research Agent**: Multi-tier grant discovery with LLM enhancement
- **Compliance Agent**: Business logic and feasibility validation
- **Scoring Engine**: Weighted composite scoring algorithm
- **Vector Embeddings**: Semantic similarity matching

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+** (for backend development)
- **Node.js 18+** (for frontend development)
- **PostgreSQL** (local development)
- **API Keys**: Perplexity, Pinecone, OpenAI
- **Telegram Bot Token** (for notifications)

### 🔧 Local Development Setup

1. **Clone and Setup**:
   ```bash
   git clone https://github.com/chiziuwaga/kevin-smart-grant-finder.git
   cd kevin-smart-grant-finder
   
   # Backend setup
   python -m venv venv
   .\venv\Scripts\Activate.ps1  # Windows PowerShell
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   ```bash
   # Copy example environment file
   cp .env.example .env
   
   # Configure required variables:
   # PERPLEXITY_API_KEY=your_key_here
   # PINECONE_API_KEY=your_key_here
   # OPENAI_API_KEY=your_key_here
   # DATABASE_URL=postgresql://user:pass@localhost/dbname
   ```

3. **Database Setup**:
   ```bash
   # Initialize database
   alembic upgrade head
   
   # Run database tests
   python test_db.py
   ```

4. **Start Development Servers**:
   ```bash
   # Backend (Terminal 1)
   uvicorn app.main:app --reload --port 8000
   
   # Frontend (Terminal 2)
   cd frontend
   npm install
   npm start
   ```

### 🌐 Production Access

The system is live and ready for use:
- **Access the application**: https://smartgrantfinder.vercel.app/
- **Authentication**: Use password "smartgrantfinder"
- **API Documentation**: Available at the backend URL + `/api/docs`

## 🧪 Testing & Quality Assurance

### Automated Testing
```bash
# Run unit tests
pytest tests/ -v

# Run integration tests
python tests/integration_test_simple.py

# Test specific components
pytest tests/test_agents.py -v
pytest tests/test_api.py -v
```

### User Acceptance Testing (UAT)
A comprehensive UAT guide is available in `UAT_TESTING_GUIDE.md` for thorough system validation including:
- Grant search functionality testing
- Scoring system accuracy validation
- User interface evaluation
- Performance assessment

### Production Health Checks
```bash
# Backend health check
curl https://smartgrantfinder-a4e2fa159e79.herokuapp.com/health

# Database connectivity test
python test_db.py

# Service integration test
python test_services.py
```

## 📁 Project Structure

```
kevin-smart-grant-finder/
├── 📂 app/                     # FastAPI application
│   ├── main.py                 # Application entry point
│   ├── router.py               # API endpoints
│   ├── crud.py                 # Database operations
│   ├── schemas.py              # Pydantic models
│   └── dependencies.py         # Dependency injection
├── 📂 agents/                  # AI Agent system
│   ├── research_agent.py       # Grant discovery & initial scoring
│   ├── compliance_agent.py     # Business logic validation
│   └── analysis_agent.py       # Advanced analysis
├── 📂 database/                # Data persistence
│   ├── models.py               # SQLAlchemy models
│   └── session.py              # Database configuration
├── 📂 config/                  # Configuration files
│   ├── settings.py             # Application settings
│   ├── kevin_profile_config.yaml     # User profile
│   ├── compliance_rules_config.yaml  # Business rules
│   └── sector_config.yaml      # Industry classifications
├── 📂 frontend/                # React application
│   ├── src/components/         # UI components
│   ├── src/api/                # API integration
│   └── public/                 # Static assets
├── 📂 tests/                   # Test suite
│   ├── test_agents.py          # Agent testing
│   ├── test_api.py             # API testing
│   └── conftest.py             # Test configuration
├── 📂 utils/                   # Utility functions
│   ├── perplexity_client.py    # AI service client
│   ├── pinecone_client.py      # Vector DB client
│   └── notification_manager.py # Alert system
└── 📂 docs/                    # Documentation
    ├── EXECUTION_PLAN.md       # Development roadmap
    ├── UAT_TESTING_GUIDE.md    # Testing protocols
    └── DEPLOYMENT_GUIDE.md     # Deployment instructions
```

## 🚀 Deployment & Production

### Current Production Environment
- **Backend**: Heroku (https://smartgrantfinder-a4e2fa159e79.herokuapp.com/)
- **Frontend**: Vercel (https://smartgrantfinder.vercel.app/)
- **Database**: Heroku PostgreSQL
- **Vector Store**: Pinecone Cloud
- **Monitoring**: Built-in health checks and logging

### Deployment Process
```bash
# Backend deployment (automated via GitHub integration)
git push origin main  # Triggers Heroku deployment

# Frontend deployment (automated via Vercel)
git push origin main  # Triggers Vercel deployment

# Manual deployment (if needed)
cd frontend && npm run deploy
```

### Environment Variables
See `DEPLOYMENT_GUIDE.md` for complete environment configuration details.

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test thoroughly
4. Run the test suite: `pytest tests/ -v`
5. Commit your changes: `git commit -m 'Add amazing feature'`
6. Push to the branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

### Code Quality Standards
- **Python**: Follow PEP 8, use type hints, comprehensive docstrings
- **TypeScript/React**: ESLint configuration, component documentation
- **Testing**: Maintain >80% test coverage
- **Documentation**: Update README and docs for new features

## 🔗 Additional Resources

### Documentation
- 📋 [Execution Plan](EXECUTION_PLAN.md) - Development roadmap and milestones
- 🧪 [UAT Testing Guide](UAT_TESTING_GUIDE.md) - Comprehensive testing protocols
- 🚀 [Deployment Guide](DEPLOYMENT_GUIDE.md) - Production deployment instructions
- 📊 [System Wellness Report](SYSTEM_WELLNESS_REPORT.md) - System health analysis

### API Documentation
- **Swagger UI**: Available at `/api/docs` on the backend URL
- **ReDoc**: Alternative documentation at `/redoc`
- **OpenAPI Spec**: JSON specification at `/openapi.json`

## 📞 Support & Contact

For technical issues, feature requests, or general inquiries:
- Create an issue in the GitHub repository
- Check existing documentation in the `docs/` folder
- Review the UAT testing guide for validation procedures

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎯 Acknowledgments

### Technology Partners
- **Perplexity AI** - Advanced language model capabilities
- **Pinecone** - Vector database and semantic search
- **Heroku** - Cloud platform and deployment
- **Vercel** - Frontend hosting and deployment
- **PostgreSQL** - Robust database foundation

### Open Source Libraries
- **FastAPI** - Modern Python web framework
- **React** - Frontend user interface library
- **Material-UI** - React component library
- **SQLAlchemy** - Python SQL toolkit and ORM
- **Alembic** - Database migration tool

---

**System Status**: ✅ **PRODUCTION READY**  
**Last Updated**: June 12, 2025  
**Version**: 2.0.0 - Advanced Grant Finder & Analysis System