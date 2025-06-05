"""
Tests for the agents package.
"""

import pytest
from unittest.mock import AsyncMock
from datetime import datetime

from agents.research_agent import ResearchAgent
from agents.analysis_agent import AnalysisAgent
from app.models import GrantFilter

class DummySession:
    def __init__(self, fail: bool = False):
        self.fail = fail

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def execute(self, *args, **kwargs):
        if self.fail:
            raise Exception("Connection failed")
        return None


class DummySessionMaker:
    def __init__(self, fail: bool = False):
        self.fail = fail

    def __call__(self):
        return DummySession(self.fail)

@pytest.fixture
def mock_clients():
    return {
        'perplexity': AsyncMock(),
        'pinecone': AsyncMock()
    }

@pytest.mark.asyncio
async def test_research_agent_search(mock_clients):
    # Setup
    agent = ResearchAgent(
        perplexity_client=mock_clients['perplexity'],
        db_sessionmaker=DummySessionMaker(),
        pinecone_client=mock_clients['pinecone']
    )
    
    # Mock responses
    mock_clients['perplexity'].search.return_value = (
        "Title: Test Grant\n"
        "Description: Description\n"
        "Funding Amount: $1000\n"
        "Deadline: 2025-12-31\n"
        "URL: http://example.com\n"
        "Eligibility: none"
    )
    
    # Test
    results = await agent.search_grants(GrantFilter(keywords="test"))
    assert isinstance(results, list)
    assert mock_clients['perplexity'].search.call_count == 3

@pytest.mark.asyncio
async def test_analysis_agent_analyze(mock_clients):
    # Setup
    agent = AnalysisAgent(
        db_sessionmaker=DummySessionMaker(),
        pinecone_client=mock_clients['pinecone']
    )
    
    # Mock data
    test_grants = [{
        "title": "Test Grant",
        "description": "Description",
        "funding_amount": "100000",
        "deadline": datetime.now().isoformat(),
        "score": 0.8
    }]
    
    # Patch internal methods to avoid database dependency
    agent._get_existing_grant_titles = AsyncMock(return_value=set())
    agent._analyze_and_store_single_grant = AsyncMock(
        side_effect=lambda grant: {**grant, "factors": {}, "score": grant.get("score", 0)}
    )
    
    # Test
    analyzed = await agent.analyze_grants(test_grants)
    assert isinstance(analyzed, list)
    assert len(analyzed) > 0
    assert "score" in analyzed[0]
    assert "factors" in analyzed[0]