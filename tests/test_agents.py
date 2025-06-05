"""
Tests for the agents package.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from app.models import GrantFilter
from agents.research_agent import ResearchAgent
from agents.analysis_agent import AnalysisAgent
from datetime import datetime

@pytest.fixture
def mock_clients():
    return {
        'perplexity': AsyncMock(),
        'db_sessionmaker': AsyncMock(),
        'pinecone': AsyncMock()
    }

@pytest.mark.asyncio
async def test_research_agent_search(mock_clients):
    # Setup
    agent = ResearchAgent(
        perplexity_client=mock_clients['perplexity'],
        db_sessionmaker=mock_clients['db_sessionmaker'],
        pinecone_client=mock_clients['pinecone']
    )

    # Mock responses
    mock_clients['perplexity'].search.return_value = "Sample grant data"
    mock_clients['pinecone'].get_embedding.return_value = [0.1] * 10
    mock_clients['pinecone'].calculate_relevance.return_value = 0.8

    sample_grant = {"title": "Grant", "description": "Desc", "source_url": "http://example.com"}
    agent._parse_results = Mock(return_value=[sample_grant])
    agent._meets_funding_criteria = Mock(return_value=True)
    agent._meets_deadline_criteria = Mock(return_value=True)
    agent._score_and_filter_grants = AsyncMock(return_value=[sample_grant])

    # Test
    results = await agent.search_grants(GrantFilter(keywords="test"))
    assert isinstance(results, list)
    assert mock_clients['perplexity'].search.call_count >= 1

@pytest.mark.asyncio
async def test_analysis_agent_analyze(mock_clients):
    # Setup
    agent = AnalysisAgent(
        db_sessionmaker=mock_clients['db_sessionmaker'],
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
    
    # Patch internal methods to avoid DB dependency
    agent._get_existing_grant_titles = AsyncMock(return_value=set())
    agent._analyze_and_store_single_grant = AsyncMock(return_value={
        "title": "Test Grant",
        "final_score": 0.9,
        "deadline_score": 0.7,
        "funding_score": 0.8,
        "pinecone_relevance_score": 0.85,
    })
    
    # Test
    analyzed = await agent.analyze_grants(test_grants)
    assert isinstance(analyzed, list)
    assert len(analyzed) > 0
    for field in ["final_score", "deadline_score", "funding_score", "pinecone_relevance_score"]:
        assert field in analyzed[0]
