"""
Tests for the agents package.
"""

import pytest
from agents.research_agent import GrantResearchAgent
from agents.analysis_agent import GrantAnalysisAgent

def test_research_agent_initialization():
    agent = GrantResearchAgent()
    assert agent.sources == []

def test_analysis_agent_initialization():
    agent = GrantAnalysisAgent()
    assert agent.criteria == {}

def test_add_source():
    agent = GrantResearchAgent()
    source = 'https://example.com/grants'
    agent.add_source(source)
    assert source in agent.sources

def test_set_criteria():
    agent = GrantAnalysisAgent()
    criteria = {'relevance': 0.5, 'amount': 0.3, 'deadline': 0.2}
    agent.set_criteria(criteria)
    assert agent.criteria == criteria