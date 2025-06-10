"""
Tests for the agents package.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
import json

from agents.research_agent import ResearchAgent
from agents.analysis_agent import AnalysisAgent
from agents.compliance_agent import ComplianceAnalysisAgent
from app.models import GrantFilter
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
        db_session_maker=DummySessionMaker(), # Changed db_sessionmaker to db_session_maker
        config_path="tests/test_configs"
    )
      # Mock responses
    mock_clients['perplexity'].search.return_value = {
        "choices": [{
            "message": {
                "content": (
                    "Title: Test Grant\n"
                    "Description: Description\n"
                    "Funding Amount: $1000\n"
                    "Deadline: 2025-12-31\n"
                    "URL: http://example.com\n"
                    "Eligibility: none"
                )
            }
        }]
    }
      # Test
    results = await agent.search_grants(GrantFilter(keywords="test"))
    assert isinstance(results, list)
    # Verify that Perplexity was called (real agent makes multiple calls per tier + fallbacks)
    assert mock_clients['perplexity'].search.call_count > 0

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

# New comprehensive tests for ResearchAgent scoring methods

@pytest.mark.asyncio
async def test_research_agent_calculate_sector_relevance(mock_clients):
    """Test sector relevance calculation with various grant types."""
    agent = ResearchAgent(
        perplexity_client=mock_clients['perplexity'],
        db_session_maker=DummySessionMaker(), # Changed db_sessionmaker to db_session_maker
        config_path="tests/test_configs"
    )
    # Mock agent's config attributes directly if they are loaded in __init__
    agent.sector_config = {
        'sectors': [
            {'name': 'Technology', 'keywords': ['AI', 'machine learning', 'software'], 'sub_sectors': ['SaaS', 'FinTech'], 'priority_weight': 1.5},
            {'name': 'Healthcare', 'keywords': ['medical', 'pharma', 'biotech'], 'sub_sectors': ['Telemedicine', 'Medical Devices'], 'priority_weight': 1.2},
            {'name': 'Education', 'keywords': ['e-learning', 'pedagogy', 'academic'], 'sub_sectors': ['EdTech', 'Vocational Training'], 'priority_weight': 1.0}
        ]
    }
    agent.user_profile = { # Ensure user_profile is also mocked if used by the method
        'business_profile': {
            'target_sectors': ['technology', 'healthcare', 'education'] # Example, adjust as needed
        }
    }

    # Test high relevance - grant in target sector
    grant_tech = {
        'title': 'Tech Innovation Grant',
        'description': 'Technology startup funding for AI and machine learning',
        'purpose': 'Advance technological innovation',
        'identified_sector': 'technology'
    }
    score = agent._calculate_sector_relevance(grant_tech)
    assert score >= 0.8, "Technology sector should have high relevance"
    
    # Test medium relevance - related keywords but different sector  
    grant_related = {
        'title': 'Digital Health Initiative',
        'description': 'Healthcare technology solutions',
        'purpose': 'Improve healthcare through technology',
        'identified_sector': 'healthcare'
    }
    score = agent._calculate_sector_relevance(grant_related)
    assert score >= 0.6, "Healthcare with tech keywords should have good relevance"
    
    # Test low relevance - unrelated sector
    grant_unrelated = {
        'title': 'Agriculture Subsidy',
        'description': 'Traditional farming support',
        'purpose': 'Support traditional agriculture',
        'identified_sector': 'agriculture'
    }
    score = agent._calculate_sector_relevance(grant_unrelated)
    assert score <= 0.4, "Unrelated sector should have low relevance"

@pytest.mark.asyncio
async def test_research_agent_calculate_geographic_relevance(mock_clients):
    """Test geographic relevance calculation."""
    agent = ResearchAgent(
        perplexity_client=mock_clients['perplexity'],
        db_session_maker=DummySessionMaker(), # Changed db_sessionmaker to db_session_maker
        config_path="tests/test_configs"
    )
    # Mock agent's config attributes
    agent.geographic_config = {
        'geographic_preferences': [
            {'region_type': 'State', 'region_name': 'California', 'priority': 'high', 'keywords': ['CA', 'California specific']},
            {'region_type': 'City', 'region_name': 'San Francisco', 'priority': 'medium', 'keywords': ['SF', 'Bay Area']},
            {'region_type': 'Country', 'region_name': 'USA', 'priority': 'low', 'keywords': ['national', 'federal']}
        ]
    }
    agent.user_profile = { # Mock user_profile if it's used by the method
        'location': {
            'primary_focus_state': 'California',
            'primary_focus_city': 'San Francisco',
            'country': 'USA'
        }
    }

    # Test high relevance - grant specific to a high-priority region
    grant_california = {
        'geographic_scope': 'California',
        'specific_location_mentions': ['San Francisco', 'Los Angeles']
    }
    score = agent._calculate_geographic_relevance(grant_california)
    assert score >= 0.9, "California-specific grant should have perfect relevance"
    
    # Test national scope
    grant_national = {
        'geographic_scope': 'National, USA',
        'specific_location_mentions': []
    }
    score = agent._calculate_geographic_relevance(grant_national)
    assert score >= 0.7, "National grants should have good relevance"
    
    # Test international scope
    grant_international = {
        'geographic_scope': 'International',
        'specific_location_mentions': ['Europe', 'Asia']
    }
    score = agent._calculate_geographic_relevance(grant_international)
    assert 0.7 <= score <= 0.85, f"International score {score} not in expected range"

@pytest.mark.asyncio
async def test_research_agent_calculate_operational_alignment(mock_clients):
    """Test operational alignment calculation."""
    agent = ResearchAgent(
        perplexity_client=mock_clients['perplexity'],
        db_session_maker=DummySessionMaker(), # Changed db_sessionmaker to db_session_maker
        config_path="tests/test_configs"
    )
      # Mock Kevin's operational capacity
    with patch.object(agent, 'user_profile', {
        'operational_capacity': {
            'team_size_fte': 5,
            'annual_revenue': 500000,
            'technical_expertise': ['software development', 'data analysis'],
            'project_management_capacity': 'medium'
        }
    }):
        
        # Test well-aligned grant
        grant_aligned = {
            'funding_amount_min': 10000,
            'funding_amount_max': 100000,
            'description': 'Software development project requiring data analysis expertise',
            'keywords': ['software', 'development', 'data', 'small team']
        }
        score = agent._calculate_operational_alignment(grant_aligned)
        assert score >= 0.7, "Well-aligned grant should have high operational score"
        
        # Test misaligned funding amount
        grant_too_large = {
            'funding_amount_min': 1000000,
            'funding_amount_max': 5000000,
            'description': 'Large enterprise software project',
            'keywords': ['enterprise', 'large scale']
        }
        score = agent._calculate_operational_alignment(grant_too_large)
        assert score <= 0.4, "Grant too large should have low operational score"

@pytest.mark.asyncio
async def test_research_agent_enrich_grant_with_llm(mock_clients):
    """Test LLM enrichment of grants."""
    agent = ResearchAgent(
        perplexity_client=mock_clients['perplexity'],
        db_session_maker=DummySessionMaker(), # Changed db_sessionmaker to db_session_maker
        config_path="tests/test_configs"
    )
    
    # Mock LLM response
    mock_llm_response = json.dumps({
        "summary": "AI research grant for machine learning projects",
        "eligibility_summary": "Open to tech startups with AI focus",
        "sector": "technology",
        "sub_sector": "artificial intelligence",
        "geographic_scope": "National, USA",
        "keywords": ["AI", "machine learning", "startups"],
        "funding_details": {
            "min": 25000,
            "max": 100000,
            "display": "$25,000 - $100,000"
        }
    })
    
    mock_clients['perplexity'].ask.return_value = mock_llm_response
    
    # Test grant enrichment
    base_grant = {
        'title': 'AI Research Grant',
        'description': 'Funding for artificial intelligence research',
        'source_url': 'https://example.com/grant'
    }
    
    enriched = await agent._enrich_grant_with_llm(base_grant)
    
    assert enriched['summary_llm'] == "AI research grant for machine learning projects"
    assert enriched['identified_sector'] == "technology"
    assert enriched['identified_sub_sector'] == "artificial intelligence"
    assert enriched['keywords'] == ["AI", "machine learning", "startups"]
    assert enriched['funding_amount_min'] == 25000
    assert enriched['funding_amount_max'] == 100000
    
    # Verify LLM was called with correct prompt
    mock_clients['perplexity'].ask.assert_called_once()
    call_args = mock_clients['perplexity'].ask.call_args
    assert "AI Research Grant" in call_args[0][0]  # Grant title in prompt
    assert "artificial intelligence research" in call_args[0][0]  # Description in prompt

@pytest.mark.asyncio
async def test_research_agent_tiered_search_functionality(mock_clients):
    """Test the tiered search functionality."""
    agent = ResearchAgent(
        perplexity_client=mock_clients['perplexity'],
        db_session_maker=DummySessionMaker(), # Changed db_sessionmaker to db_session_maker
        config_path="tests/test_configs"
    )
    
    # Mock successful tier 1 search
    tier1_response = {
        "choices": [{
            "message": {
                "content": """
Title: Tech Innovation Grant
Description: Funding for technology startups
Funding Amount: $50,000
Deadline: 2025-06-30
URL: https://example.com/tech-grant
Eligibility: Technology companies
"""
            }
        }]
    }
    
    mock_clients['perplexity'].search.return_value = tier1_response
    
    # Mock the enrichment method
    agent._enrich_grant_with_llm = AsyncMock(return_value={
        'title': 'Tech Innovation Grant',
        'description': 'Funding for technology startups',
        'funding_amount_display': '$50,000',
        'deadline_date': datetime(2025, 6, 30),
        'source_url': 'https://example.com/tech-grant',
        'eligibility_summary_llm': 'Technology companies',
        'summary_llm': 'Grant for tech startups',
        'identified_sector': 'technology',
        'research_scores': ResearchContextScores(
            sector_relevance=0.9,
            geographic_relevance=0.8,
            operational_alignment=0.7
        )
    })
    
    # Test search with filters
    grant_filter = GrantFilter(
        keywords="technology startup funding",
        min_funding=10000,
        max_funding=100000
    )
    
    results = await agent.search_grants(grant_filter)
    
    assert len(results) > 0
    assert results[0]['title'] == 'Tech Innovation Grant'
    assert results[0]['identified_sector'] == 'technology'
    assert 'research_scores' in results[0]
    
    # Verify search was called (tiered search makes multiple calls)
    assert mock_clients['perplexity'].search.call_count >= 1

# Tests for ComplianceAnalysisAgent

@pytest.mark.asyncio 
async def test_compliance_agent_business_logic_alignment():
    """Test business logic alignment calculation."""
    
    # Mock compliance rules and Kevin profile
    compliance_rules = {
        'business_logic_rules': {
            'prohibited_grant_keywords': ['gambling', 'tobacco', 'weapons'],
            'ethical_red_flags_keywords': ['discrimination', 'harmful']
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
        }
    }
    
    # Create agent with mocked config
    with patch('builtins.open'), \
         patch('yaml.safe_load', side_effect=[compliance_rules, kevin_profile]):
        
        agent = ComplianceAnalysisAgent(
            compliance_config_path='mock_compliance.yaml',
            profile_config_path='mock_profile.yaml',
            perplexity_client=AsyncMock()
        )
        
        # Test clean grant (should score high)
        clean_grant = EnrichedGrant(
            id="test-1",
            title="Clean Technology Grant",
            description="Funding for renewable energy solutions",
            purpose="Advance clean technology",
            eligibility=GrantSourceDetails(raw_text="Open to for-profit companies")
        )
        
        score = await agent._calculate_business_logic_alignment(clean_grant)
        assert score >= 0.9, "Clean grant should have high business logic score"
        
        # Test grant with prohibited keyword
        prohibited_grant = EnrichedGrant(
            id="test-2", 
            title="Gambling Platform Development",
            description="Create online gambling platform",
            purpose="Develop gambling software",
            eligibility=GrantSourceDetails(raw_text="Open to all companies")
        )
        
        score = await agent._calculate_business_logic_alignment(prohibited_grant)
        assert score <= 0.5, "Grant with prohibited keywords should have low score"
        
        # Test grant type mismatch (non-profit only)
        mismatch_grant = EnrichedGrant(
            id="test-3",
            title="Non-Profit Community Grant", 
            description="Community service funding",
            purpose="Support community initiatives",
            eligibility=GrantSourceDetails(raw_text="Open to non-profit organizations only")
        )
        
        score = await agent._calculate_business_logic_alignment(mismatch_grant)
        assert score <= 0.7, "Non-profit only grant should have reduced score for for-profit company"

@pytest.mark.asyncio
async def test_compliance_agent_feasibility_context():
    """Test feasibility context calculation."""
    
    compliance_rules = {
        'feasibility_context_rules': {
            'max_match_funding_percentage': 25,
            'acceptable_reporting_frequencies': ['quarterly', 'annually']
        },
        'scoring_weights': {
            'business_logic_alignment': 0.3,
            'feasibility_context': 0.4, 
            'strategic_synergy': 0.3
        }
    }
    
    kevin_profile = {
        'operational_capacity': {
            'team_size_fte': 5,
            'reporting_capacity': 'quarterly',
            'technical_expertise': ['software development', 'data analysis']
        }
    }
    
    with patch('builtins.open'), \
         patch('yaml.safe_load', side_effect=[compliance_rules, kevin_profile]):
        
        agent = ComplianceAnalysisAgent(
            compliance_config_path='mock_compliance.yaml',
            profile_config_path='mock_profile.yaml', 
            perplexity_client=AsyncMock()
        )
        
        # Test feasible grant
        feasible_grant = EnrichedGrant(
            id="test-1",
            title="Software Development Grant",
            description="Build web application",
            details=GrantSourceDetails(reporting_requirements="quarterly reports required")
        )
        
        score = await agent._calculate_feasibility_context(feasible_grant)
        assert score >= 0.8, "Feasible grant should have high feasibility score"
        
        # Test grant with challenging reporting requirements
        challenging_grant = EnrichedGrant(
            id="test-2",
            title="High-Maintenance Grant",
            description="Complex project with intensive oversight",
            details=GrantSourceDetails(reporting_requirements="monthly detailed reports required")
        )
        
        score = await agent._calculate_feasibility_context(challenging_grant)
        assert score <= 0.8, "Grant with monthly reporting should have reduced feasibility"

@pytest.mark.asyncio
async def test_compliance_agent_strategic_synergy():
    """Test strategic synergy calculation."""
    
    compliance_rules = {
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
            perplexity_client=AsyncMock()
        )
        
        # Test highly synergistic grant
        synergistic_grant = EnrichedGrant(
            id="test-1",
            title="Technology Innovation Grant",
            description="Funding for scalable technology solutions",
            purpose="Drive market expansion through innovation"
        )
        
        score = await agent._calculate_strategic_synergy(synergistic_grant)
        assert score >= 0.6, "Synergistic grant should have good strategic alignment"
        
        # Test misaligned grant
        misaligned_grant = EnrichedGrant(
            id="test-2", 
            title="Agricultural Equipment Grant",
            description="Funding for farming equipment and agriculture technology",
            purpose="Support traditional agriculture practices"
        )
        
        score = await agent._calculate_strategic_synergy(misaligned_grant)
        assert score <= 0.4, "Misaligned grant should have low strategic synergy"

@pytest.mark.asyncio
async def test_compliance_agent_full_analysis():
    """Test complete grant analysis workflow."""
    
    compliance_rules = {
        'business_logic_rules': {
            'prohibited_grant_keywords': [],
            'ethical_red_flags_keywords': []
        },
        'feasibility_context_rules': {
            'acceptable_reporting_frequencies': ['quarterly']
        },
        'strategic_synergy_rules': {
            'synergistic_keywords': ['technology'],
            'misaligned_focus_areas': []
        },
        'scoring_weights': {
            'business_logic_alignment': 0.3,
            'feasibility_context': 0.4,
            'strategic_synergy': 0.3
        }
    }
    
    kevin_profile = {
        'business_profile': {'type': 'For-Profit'},
        'operational_capacity': {'reporting_capacity': 'quarterly'},
        'strategic_goals': {'primary_objectives': ['technology']}
    }
    
    with patch('builtins.open'), \
         patch('yaml.safe_load', side_effect=[compliance_rules, kevin_profile]):
        
        agent = ComplianceAnalysisAgent(
            compliance_config_path='mock_compliance.yaml',
            profile_config_path='mock_profile.yaml',
            perplexity_client=AsyncMock()
        )
        
        # Test complete analysis
        test_grant = EnrichedGrant(
            id="test-1",
            title="Technology Innovation Grant",
            description="Funding for technology development",
            purpose="Advance technology solutions",
            eligibility=GrantSourceDetails(raw_text="Open to for-profit companies"),
            research_scores=ResearchContextScores(
                sector_relevance=0.9,
                geographic_relevance=0.8,
                operational_alignment=0.7
            )
        )
        
        result = await agent.analyze_grant(test_grant)
        
        # Verify compliance scores were calculated
        assert result.compliance_scores is not None
        assert result.compliance_scores.business_logic_alignment is not None
        assert result.compliance_scores.feasibility_score is not None # Changed from feasibility_context
        assert result.compliance_scores.strategic_synergy is not None
        assert result.compliance_scores.final_weighted_score is not None
        
        # Verify final weighted score is reasonable
        assert 0.0 <= result.compliance_scores.final_weighted_score <= 1.0
        
        # Verify status was updated
        assert result.record_status == "COMPLIANCE_SCORED"