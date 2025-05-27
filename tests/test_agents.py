"""
Tests for the agents package.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from agents.research_agent import ResearchAgent
from agents.analysis_agent import AnalysisAgent
from datetime import datetime

@pytest.fixture
def mock_clients():
    return {
        'perplexity': AsyncMock(),
        'mongodb': AsyncMock(),
        'pinecone': AsyncMock()
    }

@pytest.mark.asyncio
async def test_research_agent_search(mock_clients):
    # Setup
    agent = ResearchAgent(
        perplexity_client=mock_clients['perplexity'],
        mongodb_client=mock_clients['mongodb'],
        pinecone_client=mock_clients['pinecone']
    )
    
    # Mock responses
    mock_clients['perplexity'].query.return_value = "Sample grant data"
    mock_clients['pinecone'].get_embedding.return_value = [0.1] * 10
    mock_clients['pinecone'].calculate_relevance.return_value = 0.8
    
    # Test
    results = await agent.search_grants({"keywords": "test"})
    assert isinstance(results, list)
    mock_clients['perplexity'].query.assert_called_once()

@pytest.mark.asyncio
async def test_analysis_agent_analyze(mock_clients):
    # Setup
    agent = AnalysisAgent(
        mongodb_client=mock_clients['mongodb'],
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
    
    # Mock existing grants
    mock_clients['mongodb'].grants.distinct.return_value = []
    
    # Test
    analyzed = await agent.analyze_grants(test_grants)
    assert isinstance(analyzed, list)
    assert len(analyzed) > 0
    assert "score" in analyzed[0]
    assert "factors" in analyzed[0]