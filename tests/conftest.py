"""
Test configuration and fixtures for pytest.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from agents.research_agent import ResearchAgent
from agents.compliance_agent import ComplianceAnalysisAgent
from app.schemas import EnrichedGrant, ResearchContextScores, ComplianceScores, GrantSourceDetails


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


class DummyFailingSessionMaker:
    def __call__(self):
        return DummySession(fail=True)


@pytest.fixture
def failing_mock_clients():
    """Mock clients that simulate API failures."""
    perplexity_mock = AsyncMock()
    perplexity_mock.search.side_effect = Exception("API Connection Failed")
    perplexity_mock.ask.side_effect = Exception("API Connection Failed")
    
    pinecone_mock = AsyncMock()
    pinecone_mock.query.side_effect = Exception("Vector DB Connection Failed")
    
    return {
        'perplexity': perplexity_mock,
        'pinecone': pinecone_mock
    }


@pytest.fixture
def research_agent_with_configs():
    """Create a ResearchAgent instance with mocked configurations for testing."""
    mock_perplexity = AsyncMock()
    mock_session_maker = DummySessionMaker()
    
    # Mock the agent's config loading to avoid file dependencies
    with patch.object(ResearchAgent, '_load_config', return_value={}):
        
        agent = ResearchAgent(
            perplexity_client=mock_perplexity,
            db_session_maker=mock_session_maker,
            config_path="tests/test_configs"
        )
        
        # Set up mock configurations
        agent.sector_config = {
            'priority_keywords': [{'keyword': 'test', 'priority': 'High', 'weight': 0.8}],
            'secondary_keywords': [], 
            'exclusion_keywords': [], 
            'priority_weight': 0.7,
            'default_relevance_score': 0.1
        }
        
        agent.geographic_config = {
            'priority_keywords': [{'keyword': 'local', 'priority': 'High', 'weight': 0.8}],
            'secondary_keywords': [], 
            'exclusion_keywords': [], 
            'priority_weight': 0.6,
            'national_scope_boost': 0.1, 
            'default_relevance_score': 0.2
        }
        
        agent.kevin_profile_config = {
            'focus_areas_keywords': ['generic', 'test'], 
            'expertise_keywords': ['testing'],
            'project_constraints': {'negative_keywords_in_grant': ['forbidden']},
            'strategic_goals_keywords': ['development']
        }
        
        # Mock the logger
        agent.logger = MagicMock()
        
        return agent


@pytest.fixture 
def sample_enriched_grant():
    """Create a sample EnrichedGrant for testing."""
    return EnrichedGrant(
        grant_id="test-grant-001",
        title="Sample Technology Grant",
        description_grant="Funding for innovative technology solutions",
        source_url="https://example.com/grants/tech-001",
        amount=50000,
        deadline=datetime.now(timezone.utc),
        eligibility_criteria="Open to small businesses",
        summary_llm="AI-generated summary of technology grant",
        keywords=["technology", "innovation", "startup"],
        geographic_scope="National, USA",
        specific_location_mentions=["California", "New York"],
        research_scores=ResearchContextScores(
            sector_relevance=0.9,
            geographic_relevance=0.8,
            operational_alignment=0.7
        ),
        compliance_scores=ComplianceScores(
            business_logic_alignment=0.85,
            feasibility_score=0.75,
            strategic_synergy=0.8,
            final_weighted_score=0.8
        ),
        enrichment_log=["Initial creation", "LLM analysis complete"],
        raw_data_json='{"source": "test", "processed": true}'
    )


@pytest.fixture
def compliance_agent_with_mocked_config():
    """Create a ComplianceAnalysisAgent with mocked configuration."""
    mock_perplexity = AsyncMock()
    
    compliance_rules = {
        'business_logic_rules': {
            'prohibited_grant_keywords': ['gambling', 'tobacco', 'weapons'],
            'ethical_red_flags_keywords': ['discrimination', 'harmful']
        },
        'feasibility_context_rules': {
            'max_match_funding_percentage': 25,
            'acceptable_reporting_frequencies': ['quarterly', 'annually']
        },
        'strategic_synergy_rules': {
            'synergistic_keywords': ['innovation', 'scalability', 'market expansion'],
            'misaligned_focus_areas': ['agriculture', 'mining', 'oil']
        },
        'scoring_weights': {
            'business_logic_alignment': 0.3,
            'feasibility_context': 0.4,
            'strategic_synergy': 0.3
        }
    }
    
    kevin_profile = {
        'business_profile': {
            'type': 'For-Profit',
            'target_sectors': ['technology']
        },
        'operational_capacity': {
            'team_size_fte': 5,
            'reporting_capacity': 'quarterly',
            'technical_expertise': ['software development', 'data analysis']
        },
        'strategic_goals': {
            'primary_objectives': ['technology innovation', 'market growth'],
            'target_sectors': ['technology', 'fintech'],
            'long_term_vision': 'Leading technology solutions provider'
        }
    }
    
    with patch('builtins.open'), \
         patch('yaml.safe_load', side_effect=[compliance_rules, kevin_profile]):
        
        agent = ComplianceAnalysisAgent(
            compliance_config_path='mock_compliance.yaml',
            profile_config_path='mock_profile.yaml',
            perplexity_client=mock_perplexity
        )
        
        return agent
