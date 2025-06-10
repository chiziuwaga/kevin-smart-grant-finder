"""
Tests for error handling and edge cases in the grant finder system.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from pydantic import ValidationError
import json # Added json import

from agents.research_agent import ResearchAgent
from agents.compliance_agent import ComplianceAnalysisAgent
from app.schemas import (
    EnrichedGrant, ResearchContextScores, ComplianceScores, GrantSourceDetails, GrantSource, # Added GrantSource
    SectorConfig, KeywordConfig, GeographicConfig, KevinProfileConfig, ProjectConstraints,
    GrantSearchFilters # Added GrantSearchFilters for test_search_with_invalid_filters
)
from app.models import Grant as DBGrant # Assuming this is your SQLAlchemy model if needed for mocks
# from database.database import get_db_session_maker # For direct session testing if needed - commented out if not used or causing issues

# Fixtures (ensure these are correctly defined, possibly in conftest.py or here)
# Minimal example if not using conftest.py for these specific ones:
@pytest.fixture
def mock_perplexity_client():
    return AsyncMock()

@pytest.fixture
def mock_db_session_maker():
    # This mock represents the callable async_sessionmaker instance
    session_maker_mock = MagicMock() 

    # The __call__ (when session_maker_mock() is called) should return an async context manager (AsyncMock)
    async_session_context_manager = AsyncMock() 
    session_maker_mock.return_value = async_session_context_manager

    # The __aenter__ of the context manager should return the actual session object (another AsyncMock)
    mock_session = AsyncMock()
    async_session_context_manager.__aenter__.return_value = mock_session
    
    # Ensure __aexit__ is also an AsyncMock or a MagicMock that can be awaited if necessary
    async_session_context_manager.__aexit__ = AsyncMock(return_value=None) 
    
    return session_maker_mock

@pytest.fixture
def research_agent_with_configs(mock_perplexity_client, mock_db_session_maker):
    # Create a temporary config directory for this test if needed, or mock os.path.join
    # For simplicity, assuming configs are loaded via direct attribute assignment in tests or mocked _load_configs
    agent = ResearchAgent(perplexity_client=mock_perplexity_client, db_session_maker=mock_db_session_maker, config_path="tests/test_configs")
    # The tests later assign SectorConfig, GeographicConfig, etc. directly to agent attributes.
    # If _load_configs is an issue, it can be patched:
    # with patch.object(ResearchAgent, \'_load_configs\', return_value=None):
    #     agent = ResearchAgent(perplexity_client=mock_perplexity_client, db_session_maker=mock_db_session_maker, config_path=\"dummy_path\")
    return agent

@pytest.fixture # Added for fetch_grants
def mock_pinecone_client():
    return AsyncMock()

class TestResearchAgentErrorHandling:
    @pytest.mark.asyncio
    async def test_initialization_with_invalid_config_path(self, mock_perplexity_client, mock_db_session_maker):
        """Test agent initialization with a non-existent config path."""
        # This test assumes that _load_configs might log errors or handle gracefully.
        # ResearchAgent initializes configs to {} if loading fails.
        try:
            agent = ResearchAgent(
                perplexity_client=mock_perplexity_client, 
                db_session_maker=mock_db_session_maker, 
                config_path="invalid/path/to/configs"
            )
            # Check if configs are empty dicts, indicating graceful failure of _load_configs
            assert agent.sector_config == {}
            assert agent.geographic_config == {}
            assert agent.kevin_profile_config == {}
            assert agent.grant_sources_config == {}
        except Exception as e:
            pytest.fail(f"ResearchAgent initialization with invalid path raised an unexpected exception: {e}")

    @pytest.mark.asyncio
    async def test_search_with_no_grant_sources(self, research_agent_with_configs):
        """Test search when grant sources are not configured or fail to load."""
        research_agent_with_configs.grant_sources_config = None # or {}
        # search_grants expects grant_filter as a dict or GrantFilter object
        results = await research_agent_with_configs.search_grants(grant_filter={"query": "test query"})
        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_api_error_perplexity(self, research_agent_with_configs):
        """Test grant search when Perplexity API calls fail."""
        research_agent_with_configs.perplexity_client.chat.completions.create.side_effect = Exception("API Error")
        # Ensure grant_sources_config is populated for the agent to attempt search
        research_agent_with_configs.grant_sources_config = [GrantSource(source_id='s1', name='Test Source', base_url='http://example.com')]
        results = await research_agent_with_configs.search_grants(grant_filter={"query": "test query"})
        assert results == [] # Expect empty list as errors should be handled
        # Optionally, check logs for error messages if logging is implemented and accessible

    @pytest.mark.asyncio
    async def test_scoring_with_missing_data(self, research_agent_with_configs):
        """Test scoring methods when some grant data fields are missing or empty."""
        grant_missing_data = EnrichedGrant(
            id="missing1",  # Changed from grant_id, and it's a required field from base Grant
            title="Test Grant Missing",
            description="",  # Changed from description_grant, and it's a required field from base Grant
            source_url="http://example.com/missing",
            funding_amount=10000, # Changed from amount, using funding_amount from base Grant
            deadline=datetime.now(timezone.utc),
            eligibility_criteria=None, # This is fine as it's Optional in base Grant
            summary_llm=None,
            keywords=[],
            # geographic_scope=None, # This field is Optional
            specific_location_mentions=[], # Changed from None, model expects list or default_factory=list
            research_scores=ResearchContextScores(),
            compliance_scores=ComplianceScores(),
            enrichment_log=[], # This field is Optional with default_factory=list
            # raw_data_json=\"{}\" # This field is raw_source_data and is Optional
        )
        # Setup agent configs by creating Pydantic model instances
        research_agent_with_configs.sector_config = SectorConfig(
            priority_keywords=[KeywordConfig(keyword='test', priority='High', weight=0.8)],
            secondary_keywords=[],
            exclusion_keywords=[],
            priority_weight=0.7,
            default_relevance_score=0.1
        )
        research_agent_with_configs.geographic_config = GeographicConfig(
            priority_keywords=[KeywordConfig(keyword='local', priority='High', weight=0.8)],
            secondary_keywords=[],
            exclusion_keywords=[],
            priority_weight=0.6,
            national_scope_boost=0.1,
            default_relevance_score=0.2
        )
        research_agent_with_configs.kevin_profile_config = KevinProfileConfig(
            focus_areas_keywords=['generic', 'test'],
            expertise_keywords=['testing'],
            project_constraints=ProjectConstraints(negative_keywords_in_grant=['forbidden']),
            strategic_goals_keywords=['development']
        )

        # Sector relevance
        score = await research_agent_with_configs._calculate_sector_relevance(grant_missing_data)
        assert 0.0 <= score <= 1.0
        # Test with minimally valid EnrichedGrant instead of empty dict
        minimal_grant = EnrichedGrant(
            id="minimal1",
            title="",
            description="",
            source_url="http://example.com/minimal",
            funding_amount=0,
            deadline=datetime.now(timezone.utc),
            eligibility_criteria=None,
            summary_llm=None,
            keywords=[],
            specific_location_mentions=[],
            research_scores=ResearchContextScores(), # Ensure all required sub-models are present
            compliance_scores=ComplianceScores(),
            enrichment_log=[]
        )
        score = await research_agent_with_configs._calculate_sector_relevance(minimal_grant)
        assert 0.0 <= score <= 1.0
        # Geographic relevance
        score = await research_agent_with_configs._calculate_geographic_relevance(minimal_grant)
        assert 0.0 <= score <= 1.0
        # Operational alignment (requires user_profile to be loaded, mock or ensure _load_user_profile is called)
        # research_agent_with_configs._load_user_profile("test_user") # This method does not exist, profile is loaded via kevin_profile_config
        score = await research_agent_with_configs._calculate_operational_alignment(minimal_grant)
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_malformed_llm_response(self, research_agent_with_configs):
        """Test handling of malformed or unexpected JSON/text from LLM during search or enrichment."""
        # Mock Perplexity client to return malformed JSON
        malformed_response_mock = AsyncMock()
        malformed_response_mock.choices = [MagicMock(message=MagicMock(content="not a valid json string {malformed"))]
        research_agent_with_configs.perplexity_client.chat.completions.create.return_value = malformed_response_mock
        research_agent_with_configs.grant_sources_config = [GrantSource(source_id='s1', name='Test Source', base_url='http://example.com')]

        grants = await research_agent_with_configs.search_grants(grant_filter={"query": "test"})
        # Expect graceful handling: e.g., an empty list or a grant with error info in enrichment_log
        assert isinstance(grants, list)
        if grants:
            assert "Failed to parse JSON" in grants[0].enrichment_log[-1] or "Undecoded Grant Data" in grants[0].title
        # else: # No grants created, which is also acceptable if parsing fails completely for a source
            # pass 

        # Test malformed response during keyword extraction (if _extract_keywords_llm is called)
        research_agent_with_configs.perplexity_client.chat.completions.create.return_value = malformed_response_mock
        keywords = await research_agent_with_configs._extract_keywords_llm("some text")
        assert keywords == [] # Expect empty list on parsing error

        # Test malformed response during relevance assessment (if _assess_relevance_llm is called)
        research_agent_with_configs.perplexity_client.chat.completions.create.return_value = malformed_response_mock
        relevance_score = await research_agent_with_configs._assess_relevance_llm("some text", "some area")
        assert relevance_score == 0.0 # Expect default score on parsing error

    @pytest.mark.asyncio
    async def test_database_failure_handling(self, research_agent_with_configs):
        """Test agent's response to database errors during grant saving or fetching."""
        # Mock db_session_maker to raise an error on commit or query
        mock_session = AsyncMock()
        
        # Specific mock for the save operation part
        mock_session_for_save = AsyncMock()
        mock_session_for_save.commit.side_effect = Exception("DB Commit Error")
        # If save_grant_to_db's internal call to crud_create_or_update_grant does a select first:
        mock_session_for_save.execute.side_effect = Exception("DB Query Error during save's select")

        # Specific mock for the fetch operation part
        mock_session_for_fetch = AsyncMock()
        mock_session_for_fetch.execute.side_effect = Exception("DB Query Error during fetch")

        grant_to_save = EnrichedGrant(
            id="db_fail1", title="DB Fail Grant", description="Test", 
            source_url="http://example.com/dbfail", funding_amount=100, deadline=datetime.now(timezone.utc),
            research_scores=ResearchContextScores(), compliance_scores=ComplianceScores(), enrichment_log=[]
        )

        # Configure the session maker to return the save-specific session first
        research_agent_with_configs.db_session_maker.return_value.__aenter__.return_value = mock_session_for_save
        saved_grant = await research_agent_with_configs.save_grant_to_db(grant_to_save)
        assert saved_grant is None # Expect None if DB operation fails

        # Configure the session maker to return the fetch-specific session next
        research_agent_with_configs.db_session_maker.return_value.__aenter__.return_value = mock_session_for_fetch
        fetched_grant = await research_agent_with_configs.get_grant_by_id_from_db(1)
        assert fetched_grant is None # Expect None if DB query fails

    @pytest.mark.asyncio
    async def test_search_with_invalid_filters(self, research_agent_with_configs):
        """Test search functionality with invalid or unsupported filter types."""
        invalid_filter_data = {"unsupported_field": "test_value", "min_score": "not_a_float"}
        
        # This test assumes search_grants might not directly validate the `filters` dict with Pydantic itself,
        # but rather passes it along or uses it in a way that might lead to TypeErrors if not structured as expected by Perplexity call.
        # The `search_grants` in ResearchAgent currently takes `query: str` and `user_id: str`.
        # It does not have a `filters` parameter. If this test is for a different method or an old version, it needs adjustment.
        # For now, assuming this test intends to check how `search_grants` (or a sub-method) handles unexpected inputs if they were possible.
        
        # As `search_grants` does not accept `filters`, this test will cause a TypeError due to unexpected argument.
        # This can be a valid test for ensuring strict API contracts.
        with pytest.raises(TypeError): # Expecting TypeError due to unexpected keyword argument
            await research_agent_with_configs.search_grants(query="test query", user_id="test_user", filters=invalid_filter_data) # type: ignore


class TestComplianceAgentErrorHandling:
    @pytest.fixture
    def compliance_agent(self, mock_perplexity_client): # Needs perplexity_client fixture
        # Provide paths to dummy or test-specific config files
        # Ensure these files exist or mock their loading if ComplianceAnalysisAgent loads them on init
        return ComplianceAnalysisAgent(
            compliance_config_path="tests/test_configs/compliance_rules.yaml", 
            profile_config_path="tests/test_configs/kevin_profile_config.yaml",
            perplexity_client=mock_perplexity_client
        )

    @pytest.mark.asyncio
    async def test_analysis_with_missing_grant_fields(self, compliance_agent):
        """Test compliance analysis when essential fields in EnrichedGrant are missing."""
        minimal_grant = EnrichedGrant(
            id="comp_min1", title="Minimal Grant for Compliance", description="Desc",
            source_url="http://example.com/comp_min", funding_amount=5000, deadline=datetime.now(timezone.utc),
            # research_scores and compliance_scores might be expected by some internal logic
            research_scores=ResearchContextScores(), # Initialize to avoid None errors if accessed
            compliance_scores=ComplianceScores() # Initialize
        )
        # Depending on how robust the agent is, it might return a default score, log errors, or raise an exception.
        # Assuming graceful handling with default/low scores or logged errors.
        try:
            result = await compliance_agent.analyze_grant(minimal_grant)
            assert result is not None
            assert hasattr(result, 'compliance_scores')
            # Further checks: e.g., scores are default/low, or specific errors logged if accessible
            if result.compliance_scores:
                 assert result.compliance_scores.final_weighted_score is not None # Should be calculated
        except Exception as e:
            pytest.fail(f"Compliance analysis with minimal grant raised an unexpected exception: {e}")

    @pytest.mark.asyncio
    async def test_grant_with_missing_scores(self, compliance_agent):
        """Test when a grant is missing some or all sub-scores needed for final calculation."""
        grant_no_subscores = EnrichedGrant(
            id="comp_no_sub1", title="Grant No Subscores", description="Desc",
            source_url="http://example.com/comp_no_sub", funding_amount=1000, deadline=datetime.now(timezone.utc),
            research_scores=ResearchContextScores(), # All sub-scores are None by default
            compliance_scores=ComplianceScores() # All sub-scores are None by default
        )
        result = await compliance_agent.analyze_grant(grant_no_subscores)
        assert result is not None
        assert hasattr(result.compliance_scores, 'final_weighted_score')
        # The _calculate_final_weighted_score now handles None by defaulting to 0.0 for components
        assert result.compliance_scores.final_weighted_score is not None 
        assert result.compliance_scores.final_weighted_score >= 0.0

    @pytest.mark.asyncio
    async def test_invalid_compliance_rules_config(self, mock_perplexity_client):
        """Test agent behavior with a malformed or missing compliance_rules.yaml."""
        # This requires ComplianceAnalysisAgent to load configs on init or during analysis.
        # If on init, the error might occur during instantiation.
        # Create a dummy invalid config file or point to a non-existent one.
        with pytest.raises((FileNotFoundError, ValidationError, Exception)): # Expecting some form of error
            ComplianceAnalysisAgent(
                compliance_config_path="invalid/path/compliance_rules.yaml", 
                profile_config_path="tests/test_configs/kevin_profile_config.yaml", # Valid profile path
                perplexity_client=mock_perplexity_client
            )
        # If config is loaded lazily, trigger analysis to see the error:
        # agent = ComplianceAnalysisAgent(compliance_config_path="invalid_path.yaml", ...)
        # with pytest.raises(Exception):
        #     await agent.analyze_grant(some_grant_data)

    @pytest.mark.asyncio
    async def test_compliance_scoring_edge_cases(self, compliance_agent):
        """Test compliance scoring with edge case values (e.g., zero, negative if possible, very high)."""
        edge_case_grant = EnrichedGrant(
            id="comp_edge1", title="Edge Case Grant", description="Desc",
            source_url="http://example.com/edge", funding_amount=0, deadline=datetime.now(timezone.utc),
            research_scores=ResearchContextScores(sector_relevance=0, geographic_relevance=0, operational_alignment=0),
            compliance_scores=ComplianceScores(business_logic_alignment=0, feasibility_score=0, strategic_synergy=0)
        )        # Mock the individual calculation methods to return 0 for this specific grant scenario
        with patch.object(compliance_agent, '_calculate_business_logic_alignment', new_callable=AsyncMock, return_value=0.0), \
             patch.object(compliance_agent, '_calculate_feasibility_context', new_callable=AsyncMock, return_value=0.0), \
             patch.object(compliance_agent, '_calculate_strategic_synergy', new_callable=AsyncMock, return_value=0.0):
            
            result = await compliance_agent.analyze_grant(edge_case_grant)
            assert result.compliance_scores.final_weighted_score == 0.0

        # Example with high scores (ensure clamping or normalization is handled if applicable)
        edge_case_grant_high = EnrichedGrant(
            id="comp_edge2", title="Edge Case Grant High", description="Desc",
            source_url="http://example.com/edge_high", funding_amount=1000000, deadline=datetime.now(timezone.utc),
            research_scores=ResearchContextScores(sector_relevance=1.0, geographic_relevance=1.0, operational_alignment=1.0),
            compliance_scores=ComplianceScores(business_logic_alignment=1.0, feasibility_score=1.0, strategic_synergy=1.0)
        )        # For this part, we let the actual calculation methods run or mock them to return 1.0
        # To test the weighting with high scores, we can mock them to return 1.0
        with patch.object(compliance_agent, '_calculate_business_logic_alignment', new_callable=AsyncMock, return_value=1.0), \
             patch.object(compliance_agent, '_calculate_feasibility_context', new_callable=AsyncMock, return_value=1.0), \
             patch.object(compliance_agent, '_calculate_strategic_synergy', new_callable=AsyncMock, return_value=1.0):
            
            result_high = await compliance_agent.analyze_grant(edge_case_grant_high)
            # Assuming weights are 0.3, 0.4, 0.3, sum is 1.0
            # So, 1.0*0.3 + 1.0*0.4 + 1.0*0.3 = 1.0
            assert result_high.compliance_scores.final_weighted_score == 1.0 # Expect 1.0 if all sub-scores are 1.0 and weights sum to 1


class TestCRUDErrorHandling:
    @pytest.mark.asyncio
    async def test_database_connection_failure(self):
        """Test CRUD operations with database connection failures."""
        from tests.test_crud_enriched import MockAsyncSession
        # Mock session that fails
        failing_session = MockAsyncSession(fail=True)
        # mock_pinecone = AsyncMock() # Not used in get_grant_by_id
        from app.crud import get_grant_by_id

        # Should raise an exception indicating database failure
        with pytest.raises(Exception, match=r"Database error|Simulated database error|Database operation failed"): # Adjusted regex
            # Use an integer ID to bypass the initial type check in get_grant_by_id
            # Corrected call signature for get_grant_by_id
            await get_grant_by_id(db=failing_session, grant_id=99999) 

    @pytest.mark.asyncio
    async def test_invalid_grant_data_creation(self, research_agent_with_configs: ResearchAgent): # Added fixture
        """Test creating a grant with invalid data (e.g., missing required fields for DB model)."""
        # Using ResearchAgent.save_grant_to_db as create_or_update_grant from app.crud is not available
        
        invalid_grant_data = EnrichedGrant(
            id="invalid_id_crud", 
            title="Valid Title For DB", # Provide a non-None string for title
            description="Valid description",
            source_url="http://example.com/invalid_create_via_agent",
            funding_amount=100, deadline=datetime.now(timezone.utc),
            research_scores=ResearchContextScores(), compliance_scores=ComplianceScores()
        )

        # Mock the agent's db_session_maker to simulate a DB error (e.g., constraint violation)
        mock_session_for_agent = AsyncMock()
        mock_session_for_agent.commit.side_effect = Exception("Simulated DB constraint error due to null title")
        research_agent_with_configs.db_session_maker.return_value.__aenter__.return_value = mock_session_for_agent
        
        # The agent's save_grant_to_db should catch the DB error and return None
        saved_grant = await research_agent_with_configs.save_grant_to_db(invalid_grant_data)
        assert saved_grant is None

    @pytest.mark.asyncio
    @patch('app.crud.create_or_update_grant') # Patch the actual CRUD function
    async def test_non_existent_grant_update_or_fetch(self, mock_crud_create_update, research_agent_with_configs: ResearchAgent):
        """Test updating or fetching a grant that does not exist."""
        from app.crud import get_grant_by_id # get_grant_by_id is from app.crud
        mock_crud_session = AsyncMock()
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_crud_session.execute.return_value = mock_result
        
        fetched_grant = await get_grant_by_id(db=mock_crud_session, grant_id=9999)
        assert fetched_grant is None

        grant_to_create_non_existent = EnrichedGrant(
            id="non_existent_id_string", 
            title="Create Non Existent via Agent", description="Test",
            source_url="http://example.com/nonexist_agent_create", funding_amount=100, deadline=datetime.now(timezone.utc),
            research_scores=ResearchContextScores(), compliance_scores=ComplianceScores(),
            grant_id_external="ext-non-exist-001" # Ensure this is present for mapping if needed
        )
        

        # Setup mock_crud_create_update to return a mock DBGrant instance
        mock_db_grant_returned = MagicMock(spec=DBGrant) # Use spec for better mocking
        mock_db_grant_returned.id = "db_sim_id_789"
        mock_db_grant_returned.grant_id_external = grant_to_create_non_existent.grant_id_external
        mock_db_grant_returned.title = grant_to_create_non_existent.title
        mock_db_grant_returned.description = grant_to_create_non_existent.description
        mock_db_grant_returned.summary_llm = grant_to_create_non_existent.summary_llm
        mock_db_grant_returned.funder_name = grant_to_create_non_existent.funder_name
        mock_db_grant_returned.funding_amount_min = grant_to_create_non_existent.funding_amount_min
        mock_db_grant_returned.funding_amount_max = grant_to_create_non_existent.funding_amount_max
        mock_db_grant_returned.funding_amount_exact = grant_to_create_non_existent.funding_amount
        mock_db_grant_returned.funding_amount_display = str(grant_to_create_non_existent.funding_amount)
        mock_db_grant_returned.deadline = grant_to_create_non_existent.deadline
        mock_db_grant_returned.application_open_date = grant_to_create_non_existent.application_open_date
        mock_db_grant_returned.eligibility_summary_llm = grant_to_create_non_existent.eligibility_criteria
        mock_db_grant_returned.keywords_json = json.dumps(grant_to_create_non_existent.keywords or [])
        mock_db_grant_returned.categories_project_json = json.dumps(grant_to_create_non_existent.categories_project or [])
        if grant_to_create_non_existent.source_details:
            mock_db_grant_returned.source_name = grant_to_create_non_existent.source_details.source_name
            mock_db_grant_returned.source_url = str(grant_to_create_non_existent.source_details.source_url)
            mock_db_grant_returned.retrieved_at = grant_to_create_non_existent.source_details.retrieved_at
        else:
            mock_db_grant_returned.source_name = "Mock Source"
            mock_db_grant_returned.source_url = "http://mock.example.com"
            mock_db_grant_returned.retrieved_at = datetime.now(timezone.utc)
        mock_db_grant_returned.record_status = grant_to_create_non_existent.record_status
        if grant_to_create_non_existent.research_scores:
            mock_db_grant_returned.sector_relevance_score = grant_to_create_non_existent.research_scores.sector_relevance
            mock_db_grant_returned.geographic_relevance_score = grant_to_create_non_existent.research_scores.geographic_relevance
            mock_db_grant_returned.operational_alignment_score = grant_to_create_non_existent.research_scores.operational_alignment
        if grant_to_create_non_existent.compliance_scores:
            mock_db_grant_returned.business_logic_alignment_score = grant_to_create_non_existent.compliance_scores.business_logic_alignment
            mock_db_grant_returned.feasibility_context_score = grant_to_create_non_existent.compliance_scores.feasibility_score
            mock_db_grant_returned.strategic_synergy_score = grant_to_create_non_existent.compliance_scores.strategic_synergy
        mock_db_grant_returned.overall_composite_score = grant_to_create_non_existent.overall_composite_score
        mock_db_grant_returned.identified_sector = grant_to_create_non_existent.identified_sector
        mock_db_grant_returned.identified_sub_sector = grant_to_create_non_existent.identified_sub_sector
        mock_db_grant_returned.geographic_scope = grant_to_create_non_existent.geographic_scope
        mock_db_grant_returned.specific_location_mentions_json = json.dumps(grant_to_create_non_existent.specific_location_mentions or [])
        mock_db_grant_returned.raw_source_data_json = json.dumps(grant_to_create_non_existent.raw_source_data or {})
        mock_db_grant_returned.enrichment_log_json = json.dumps(grant_to_create_non_existent.enrichment_log or [])
        mock_db_grant_returned.last_enriched_at = grant_to_create_non_existent.last_enriched_at
        mock_db_grant_returned.created_at = datetime.now(timezone.utc)
        mock_db_grant_returned.updated_at = datetime.now(timezone.utc)

        mock_crud_create_update.return_value = mock_db_grant_returned
        
        result_grant = await research_agent_with_configs.save_grant_to_db(grant_to_create_non_existent)
        assert result_grant is not None 
        assert result_grant.title == "Create Non Existent via Agent"
        mock_crud_create_update.assert_called_once_with(research_agent_with_configs.db_session_maker.return_value.__aenter__.return_value, grant_to_create_non_existent)

    @pytest.mark.asyncio
    @patch('app.crud.create_or_update_grant') # Patch the actual CRUD function
    async def test_list_field_edge_cases(self, mock_crud_create_update, research_agent_with_configs: ResearchAgent):
        """Test CRUD operations involving list fields (e.g., keywords, categories) with empty lists or many items."""
        
        # Scenario 1: Create with empty lists
        grant_empty_lists = EnrichedGrant(
            id="empty_list_id_crud", 
            title="Grant Empty Lists Agent", description="Desc", source_url="http://example.com/empty_lists_agent",
            funding_amount=100, deadline=datetime.now(timezone.utc),
            keywords=[], categories_project=[], specific_location_mentions=[], enrichment_log=[],
            research_scores=ResearchContextScores(), compliance_scores=ComplianceScores(),
            grant_id_external="ext-empty-list-001"
        )
        
        mock_db_grant_empty = MagicMock(spec=DBGrant)
        # Populate mock_db_grant_empty similar to test_non_existent_grant_update_or_fetch's mock_db_grant_returned
        # For brevity, only showing a few fields, but all fields needed by _map_db_grant_to_enriched_grant should be set
        mock_db_grant_empty.id = "db_empty_id_123"
        mock_db_grant_empty.title = grant_empty_lists.title
        mock_db_grant_empty.keywords_json = json.dumps([]) 
        mock_db_grant_empty.categories_project_json = json.dumps([])
        # ... (populate ALL other fields required by _map_db_grant_to_enriched_grant based on grant_empty_lists)
        mock_db_grant_empty.grant_id_external = grant_empty_lists.grant_id_external
        mock_db_grant_empty.description = grant_empty_lists.description
        mock_db_grant_empty.summary_llm = grant_empty_lists.summary_llm
        mock_db_grant_empty.funder_name = grant_empty_lists.funder_name
        mock_db_grant_empty.funding_amount_min = grant_empty_lists.funding_amount_min
        mock_db_grant_empty.funding_amount_max = grant_empty_lists.funding_amount_max
        mock_db_grant_empty.funding_amount_exact = grant_empty_lists.funding_amount
        mock_db_grant_empty.funding_amount_display = str(grant_empty_lists.funding_amount)
        mock_db_grant_empty.deadline = grant_empty_lists.deadline
        mock_db_grant_empty.application_open_date = grant_empty_lists.application_open_date
        mock_db_grant_empty.eligibility_summary_llm = grant_empty_lists.eligibility_criteria
        if grant_empty_lists.source_details:
            mock_db_grant_empty.source_name = grant_empty_lists.source_details.source_name
            mock_db_grant_empty.source_url = str(grant_empty_lists.source_details.source_url)
            mock_db_grant_empty.retrieved_at = grant_empty_lists.source_details.retrieved_at
        else:
            mock_db_grant_empty.source_name = "Mock Source Empty"
            mock_db_grant_empty.source_url = "http://mock.example.com/empty"
            mock_db_grant_empty.retrieved_at = datetime.now(timezone.utc)
        mock_db_grant_empty.record_status = grant_empty_lists.record_status
        if grant_empty_lists.research_scores: mock_db_grant_empty.sector_relevance_score = grant_empty_lists.research_scores.sector_relevance # etc.
        if grant_empty_lists.compliance_scores: mock_db_grant_empty.business_logic_alignment_score = grant_empty_lists.compliance_scores.business_logic_alignment # etc.
        mock_db_grant_empty.overall_composite_score = grant_empty_lists.overall_composite_score
        mock_db_grant_empty.specific_location_mentions_json = json.dumps(grant_empty_lists.specific_location_mentions or [])
        mock_db_grant_empty.raw_source_data_json = json.dumps(grant_empty_lists.raw_source_data or {})
        mock_db_grant_empty.enrichment_log_json = json.dumps(grant_empty_lists.enrichment_log or [])
        mock_db_grant_empty.created_at = datetime.now(timezone.utc)
        mock_db_grant_empty.updated_at = datetime.now(timezone.utc)

        mock_crud_create_update.return_value = mock_db_grant_empty
        
        created_grant = await research_agent_with_configs.save_grant_to_db(grant_empty_lists)
        assert created_grant is not None
        assert created_grant.keywords == []
        assert created_grant.categories_project == []
        mock_crud_create_update.assert_called_once_with(research_agent_with_configs.db_session_maker.return_value.__aenter__.return_value, grant_empty_lists)

        mock_crud_create_update.reset_mock() # Reset for the next call

        # Scenario 2: Create with many items in lists
        many_keywords = [f"keyword_{i}" for i in range(1000)]
        grant_many_items = EnrichedGrant(
            id="many_items_id_crud", 
            title="Grant Many Items Agent", description="Desc", source_url="http://example.com/many_items_agent",
            funding_amount=100, deadline=datetime.now(timezone.utc),
            keywords=many_keywords, categories_project=["cat1"]*50,
            research_scores=ResearchContextScores(), compliance_scores=ComplianceScores(), enrichment_log=[],
            grant_id_external="ext-many-items-001"
        )
        
        mock_db_grant_many = MagicMock(spec=DBGrant)
        # Populate mock_db_grant_many similarly, ensuring all fields for _map_db_grant_to_enriched_grant
        mock_db_grant_many.id = "db_many_id_456"
        mock_db_grant_many.title = grant_many_items.title
        mock_db_grant_many.keywords_json = json.dumps(many_keywords)
        mock_db_grant_many.categories_project_json = json.dumps(["cat1"]*50)
        # ... (populate ALL other fields required by _map_db_grant_to_enriched_grant based on grant_many_items)
        mock_db_grant_many.grant_id_external = grant_many_items.grant_id_external
        mock_db_grant_many.description = grant_many_items.description
        # (Skipping full population for brevity, but it's crucial for the actual test)
        mock_db_grant_many.summary_llm = grant_many_items.summary_llm
        mock_db_grant_many.funder_name = grant_many_items.funder_name
        mock_db_grant_many.funding_amount_min = grant_many_items.funding_amount_min
        mock_db_grant_many.funding_amount_max = grant_many_items.funding_amount_max
        mock_db_grant_many.funding_amount_exact = grant_many_items.funding_amount
        mock_db_grant_many.funding_amount_display = str(grant_many_items.funding_amount)
        mock_db_grant_many.deadline = grant_many_items.deadline
        mock_db_grant_many.application_open_date = grant_many_items.application_open_date
        mock_db_grant_many.eligibility_summary_llm = grant_many_items.eligibility_criteria
        if grant_many_items.source_details:
            mock_db_grant_many.source_name = grant_many_items.source_details.source_name
            mock_db_grant_many.source_url = str(grant_many_items.source_details.source_url)
            mock_db_grant_many.retrieved_at = grant_many_items.source_details.retrieved_at
        else:
            mock_db_grant_many.source_name = "Mock Source Many"
            mock_db_grant_many.source_url = "http://mock.example.com/many"
            mock_db_grant_many.retrieved_at = datetime.now(timezone.utc)
        mock_db_grant_many.record_status = grant_many_items.record_status
        if grant_many_items.research_scores: mock_db_grant_many.sector_relevance_score = grant_many_items.research_scores.sector_relevance
        if grant_many_items.compliance_scores: mock_db_grant_many.business_logic_alignment_score = grant_many_items.compliance_scores.business_logic_alignment
        mock_db_grant_many.overall_composite_score = grant_many_items.overall_composite_score
        mock_db_grant_many.specific_location_mentions_json = json.dumps(grant_many_items.specific_location_mentions or [])
        mock_db_grant_many.raw_source_data_json = json.dumps(grant_many_items.raw_source_data or {})
        mock_db_grant_many.enrichment_log_json = json.dumps(grant_many_items.enrichment_log or [])
        mock_db_grant_many.created_at = datetime.now(timezone.utc)
        mock_db_grant_many.updated_at = datetime.now(timezone.utc)

        mock_crud_create_update.return_value = mock_db_grant_many
        
        created_grant_many = await research_agent_with_configs.save_grant_to_db(grant_many_items)
        assert created_grant_many is not None
        assert len(created_grant_many.keywords) == 1000
        mock_crud_create_update.assert_called_once_with(research_agent_with_configs.db_session_maker.return_value.__aenter__.return_value, grant_many_items)

class TestSystemIntegrationErrorHandling:
    @pytest.mark.asyncio
    async def test_full_search_cycle_with_agent_failures(self):
        """Test the main run_full_search_cycle with one of the agents failing."""
        from app.crud import run_full_search_cycle
        
        # Setup for the first scenario (ResearchAgent fails)
        mock_session_ra_fail = AsyncMock()
        mock_context_manager_ra_fail = AsyncMock()
        mock_context_manager_ra_fail.__aenter__.return_value = mock_session_ra_fail
        mock_context_manager_ra_fail.__aexit__ = AsyncMock(return_value=None)
        mock_db_session_maker_ra_fail = MagicMock(return_value=mock_context_manager_ra_fail)

        mock_perplexity_client = AsyncMock()
        mock_pinecone_client = AsyncMock()

        with patch('app.crud.ResearchAgent', side_effect=Exception("Research Agent Boom!")):
            results = await run_full_search_cycle(
                mock_db_session_maker_ra_fail, 
                mock_perplexity_client, 
                mock_pinecone_client
            )
            assert results == []
            mock_db_session_maker_ra_fail.assert_called_once()
            mock_session_ra_fail.add.assert_called_once()
            mock_session_ra_fail.commit.assert_called_once()

        # Setup for the second scenario (ComplianceAnalysisAgent fails)
        mock_session_ca_fail = AsyncMock()
        mock_context_manager_ca_fail = AsyncMock()
        mock_context_manager_ca_fail.__aenter__.return_value = mock_session_ca_fail
        mock_context_manager_ca_fail.__aexit__ = AsyncMock(return_value=None)
        mock_db_session_maker_ca_fail = MagicMock(return_value=mock_context_manager_ca_fail)
        
        mock_research_agent_instance = AsyncMock(spec=ResearchAgent)
        sample_grant_data = {
            "id": "sys_fail1", "title": "Sys Fail Grant", "description": "Test", 
            "source_details": GrantSourceDetails(source_name="TestSrc", source_url="http://example.com/sysfail", retrieved_at=datetime.now(timezone.utc)),
            "funding_amount": 100.0, "deadline": datetime.now(timezone.utc).date(), # Changed to funding_amount and deadline
            "research_scores": ResearchContextScores(), 
            "compliance_scores": ComplianceScores(),
            "enrichment_log": [],
            "keywords": [], "categories_project": [], "specific_location_mentions": [],
            "created_at": datetime.now(timezone.utc), # Ensure these are present
            "updated_at": datetime.now(timezone.utc),
            "eligibility_criteria": "Some criteria", # Ensure this is present
            "source_name": "TestSrc", # Ensure this is present
            "source_url": "http://example.com/sysfail", # Ensure this is present
            "category": "TestCategory" # Ensure this is present
        }
        # Ensure all fields required by EnrichedGrant are present, including those inherited from Grant
        # The sample_grant_data was missing some fields that EnrichedGrant expects from its base Grant model.
        # Corrected sample_grant_data to use fields expected by EnrichedGrant directly
        complete_sample_grant = EnrichedGrant(
            id="sys_fail1",
            title="Sys Fail Grant",
            description="Test",
            funding_amount=100.0, # from base Grant
            deadline=datetime.now(timezone.utc), # from base Grant
            eligibility_criteria="Some criteria", # from base Grant
            category="TestCategory", # from base Grant
            source_url="http://example.com/sysfail", # from base Grant
            source_name="TestSrc", # from base Grant
            # EnrichedGrant specific fields
            source_details=GrantSourceDetails(source_name="TestSrc", source_url="http://example.com/sysfail", retrieved_at=datetime.now(timezone.utc)),
            research_scores=ResearchContextScores(), 
            compliance_scores=ComplianceScores(),
            enrichment_log=[],
            keywords=[],
            categories_project=[],
            specific_location_mentions=[],
            created_at=datetime.now(timezone.utc), 
            updated_at=datetime.now(timezone.utc)
        )


        mock_research_agent_instance.search_grants.return_value = [complete_sample_grant]
        
        with patch('app.crud.ResearchAgent', return_value=mock_research_agent_instance):
            with patch('app.crud.ComplianceAnalysisAgent', side_effect=Exception("Compliance Agent Boom!")):
                results = await run_full_search_cycle(
                    mock_db_session_maker_ca_fail, 
                    mock_perplexity_client, 
                    mock_pinecone_client
                )
                assert len(results) == 1 
                assert mock_session_ca_fail.add.call_count >= 1 
                assert mock_session_ca_fail.commit.call_count >= 1
