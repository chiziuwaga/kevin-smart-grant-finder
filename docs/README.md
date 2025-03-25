# Kevin's Smart Grant Finder Documentation

## Overview
This directory contains comprehensive documentation for Kevin's Smart Grant Finder system.

## Contents

### Core Documentation
- `README.md` - This file, providing an overview of the documentation
- `DEPLOYMENT.md` - Deployment instructions and configuration
- `references/` - Grant resources and reference materials
  - `grant_sources.md` - Curated list of grant sources and search strategies
  - `api_integration.md` - API integration documentation

### System Architecture
The system is built with the following components:

1. Web Interface (`dashboard/`)
   - Streamlit-based dashboard
   - Interactive grant exploration
   - Analytics and metrics

2. Data Management (`database/`)
   - MongoDB for grant storage
   - Pinecone for semantic search
   - Data models and schemas

3. Grant Discovery (`agents/`)
   - Research agent for finding grants
   - Analysis agent for scoring relevance
   - Integration with multiple data sources

4. Data Collection (`scrapers/`)
   - Source-specific scrapers
   - Data validation and cleaning
   - Scheduled updates

5. API Layer (`api/`)
   - RESTful endpoints
   - Data access controls
   - Integration points

6. Configuration (`config/`)
   - Environment settings
   - API keys and credentials
   - System parameters

## Getting Started
1. Review the deployment guide in `DEPLOYMENT.md`
2. Configure the environment using `.env.example`
3. Set up the required APIs and services
4. Deploy the system components

## Contributing
- Follow the project structure
- Update documentation for new features
- Maintain test coverage
- Use consistent coding style 