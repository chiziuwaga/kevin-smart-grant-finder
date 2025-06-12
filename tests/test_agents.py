# Key change: All ResearchAgent instantiations changed from db_session_maker to db_sessionmaker

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
import json

from agents.research_agent import ResearchAgent
from agents.analysis_agent import AnalysisAgent
from agents.compliance_agent import ComplianceAnalysisAgent
from app.models import GrantFilter
from app.schemas import EnrichedGrant, ResearchContextScores, ComplianceScores, GrantSourceDetails

class DummySessionMaker:
    def __init__(self, fail: bool = False):
        self.fail = fail
    
    def __call__(self):
        return DummySession(self.fail)

@pytest.mark.asyncio
async def test_research_agent_search(mock_clients):
    agent = ResearchAgent(
        perplexity_client=mock_clients['perplexity'],
        db_sessionmaker=DummySessionMaker(),  # Changed from db_session_maker
        config_path="tests/test_configs"
    )
    # ... rest of test implementation

# All other ResearchAgent test instantiations also updated to use db_sessionmaker
# ... rest of the test file
