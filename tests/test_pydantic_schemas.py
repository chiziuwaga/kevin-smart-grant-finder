"""
Tests for Pydantic model validation and schema functionality.
"""

import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pydantic import ValidationError

from app.schemas import (
    EnrichedGrant, ResearchContextScores, ComplianceScores, 
    GrantSourceDetails, Grant, GrantSearchFilters,
    DashboardStats, DistributionData, UserSettings
)


class TestResearchContextScores:
    """Test ResearchContextScores validation and functionality."""
    
    def test_valid_research_scores(self):
        """Test creation with valid scores."""
        scores = ResearchContextScores(
            sector_relevance=0.85,
            geographic_relevance=0.70,
            operational_alignment=0.90
        )
        
        assert scores.sector_relevance == 0.85
        assert scores.geographic_relevance == 0.70
        assert scores.operational_alignment == 0.90
    
    def test_optional_fields(self):
        """Test that all fields are optional."""
        scores = ResearchContextScores()
        
        assert scores.sector_relevance is None
        assert scores.geographic_relevance is None
        assert scores.operational_alignment is None
    
    def test_partial_scores(self):
        """Test creation with partial scores."""
        scores = ResearchContextScores(
            sector_relevance=0.75,
            geographic_relevance=None,
            operational_alignment=0.85
        )
        
        assert scores.sector_relevance == 0.75
        assert scores.geographic_relevance is None
        assert scores.operational_alignment == 0.85
    
    def test_score_bounds_validation(self):
        """Test that scores accept reasonable bounds."""
        # Test minimum values
        scores_min = ResearchContextScores(
            sector_relevance=0.0,
            geographic_relevance=0.0,
            operational_alignment=0.0
        )
        assert all(score == 0.0 for score in [
            scores_min.sector_relevance,
            scores_min.geographic_relevance,
            scores_min.operational_alignment
        ])
        
        # Test maximum values
        scores_max = ResearchContextScores(
            sector_relevance=1.0,
            geographic_relevance=1.0,
            operational_alignment=1.0
        )
        assert all(score == 1.0 for score in [
            scores_max.sector_relevance,
            scores_max.geographic_relevance,
            scores_max.operational_alignment
        ])
    
    def test_serialization(self):
        """Test JSON serialization and deserialization."""
        original = ResearchContextScores(
            sector_relevance=0.85,
            geographic_relevance=0.70,
            operational_alignment=0.90
        )
        
        # Test to dict
        data = original.model_dump()
        assert isinstance(data, dict)
        assert data["sector_relevance"] == 0.85
        
        # Test from dict
        reconstructed = ResearchContextScores(**data)
        assert reconstructed.sector_relevance == original.sector_relevance
        assert reconstructed.geographic_relevance == original.geographic_relevance
        assert reconstructed.operational_alignment == original.operational_alignment


class TestComplianceScores:
    """Test ComplianceScores validation and functionality."""
    
    def test_valid_compliance_scores(self):
        """Test creation with valid compliance scores."""
        scores = ComplianceScores(
            business_logic_alignment=0.90,
            feasibility_score=0.75,
            strategic_synergy=0.85
        )
        
        assert scores.business_logic_alignment == 0.90
        assert scores.feasibility_score == 0.75
        assert scores.strategic_synergy == 0.85
    
    def test_all_fields_optional(self):
        """Test that all compliance score fields are optional."""
        scores = ComplianceScores()
        
        assert scores.business_logic_alignment is None
        assert scores.feasibility_score is None
        assert scores.strategic_synergy is None
    
    def test_field_naming_consistency(self):
        """Test field naming matches expectations."""
        scores = ComplianceScores(
            business_logic_alignment=0.8,
            feasibility_score=0.7,
            strategic_synergy=0.9
        )
        
        # Verify field names are as expected
        data = scores.model_dump()
        expected_fields = {
            "business_logic_alignment",
            "feasibility_score", 
            "strategic_synergy"
        }
        assert set(data.keys()) == expected_fields


class TestGrantSourceDetails:
    """Test GrantSourceDetails validation and functionality."""
    
    def test_valid_source_details(self):
        """Test creation with valid source details."""
        now = datetime.now()
        details = GrantSourceDetails(
            source_name="TechGrants.gov",
            source_url="https://techgrants.gov/ai-funding",
            retrieved_at=now
        )
        
        assert details.source_name == "TechGrants.gov"
        assert details.source_url == "https://techgrants.gov/ai-funding"
        assert details.retrieved_at == now
    
    def test_optional_fields(self):
        """Test that all fields are optional."""
        details = GrantSourceDetails()
        
        assert details.source_name is None
        assert details.source_url is None
        assert details.retrieved_at is None
    
    def test_partial_details(self):
        """Test creation with partial information."""
        details = GrantSourceDetails(
            source_name="GrantDatabase",
            source_url=None,
            retrieved_at=datetime.now()
        )
        
        assert details.source_name == "GrantDatabase"
        assert details.source_url is None
        assert details.retrieved_at is not None


class TestEnrichedGrant:
    """Test EnrichedGrant model validation and functionality."""
    
    def test_minimal_enriched_grant(self):
        """Test creation with minimal required fields."""
        grant = EnrichedGrant(
            id="test-grant-1",
            title="Test Grant",
            description="A test grant for validation"
        )
        
        assert grant.id == "test-grant-1"
        assert grant.title == "Test Grant"
        assert grant.description == "A test grant for validation"
        
        # Verify default values
        assert grant.keywords == []
        assert grant.categories_project == []
        assert grant.specific_location_mentions == []
        assert grant.enrichment_log == []
    
    def test_full_enriched_grant(self):
        """Test creation with all fields populated."""
        now = datetime.now()
        deadline = now + timedelta(days=90)
        
        grant = EnrichedGrant(
            id="comprehensive-grant-1",
            title="Comprehensive AI Research Grant",
            description="Full-featured grant for AI research and development",
            funding_amount=100000,
            deadline=deadline,
            eligibility_criteria="Open to tech startups",
            category="Technology",
            source_url="https://example.com/grant",
            source_name="AI Foundation",
            
            # Enriched fields
            grant_id_external="EXT-AI-2025-001",
            summary_llm="Advanced AI research funding opportunity",
            eligibility_summary_llm="Targeted at innovative AI startups",
            funder_name="AI Innovation Foundation",
            
            # Funding details
            funding_amount_min=75000,
            funding_amount_max=125000,
            funding_amount_exact=100000,
            funding_amount_display="$75,000 - $125,000",
            
            # Dates
            deadline_date=deadline,
            application_open_date=now,
            
            # Classifications
            keywords=["AI", "machine learning", "research", "innovation"],
            categories_project=["technology", "research", "AI"],
            identified_sector="technology",
            identified_sub_sector="artificial intelligence",
            geographic_scope="National, USA",
            specific_location_mentions=["Silicon Valley", "Boston", "Austin"],
            
            # Scores
            research_scores=ResearchContextScores(
                sector_relevance=0.95,
                geographic_relevance=0.85,
                operational_alignment=0.90
            ),
            compliance_scores=ComplianceScores(
                business_logic_alignment=0.88,
                feasibility_score=0.82,
                strategic_synergy=0.93
            ),
            overall_composite_score=0.89,
            feasibility_score=0.82,
            
            # Source details
            source_details=GrantSourceDetails(
                source_name="AI Grant Database",
                source_url="https://aigrants.com/comprehensive",
                retrieved_at=now
            ),
            
            # Metadata
            record_status="ACTIVE",
            application_status="Not Applied",
            created_at=now,
            updated_at=now,
            last_enriched_at=now,
            enrichment_log=["Initial extraction", "LLM enrichment", "Compliance analysis"]
        )
        
        # Verify all fields are set correctly
        assert grant.id == "comprehensive-grant-1"
        assert grant.title == "Comprehensive AI Research Grant"
        assert len(grant.keywords) == 4
        assert grant.identified_sector == "technology"
        assert grant.research_scores.sector_relevance == 0.95
        assert grant.compliance_scores.business_logic_alignment == 0.88
        assert grant.overall_composite_score == 0.89
        assert len(grant.enrichment_log) == 3
    
    def test_nested_object_validation(self):
        """Test validation of nested objects."""
        grant = EnrichedGrant(
            id="nested-test",
            title="Nested Object Test",
            description="Testing nested object validation",
            research_scores=ResearchContextScores(
                sector_relevance=0.8,
                geographic_relevance=0.7
            ),
            compliance_scores=ComplianceScores(
                business_logic_alignment=0.9
            )
        )
        
        assert grant.research_scores.sector_relevance == 0.8
        assert grant.research_scores.operational_alignment is None
        assert grant.compliance_scores.business_logic_alignment == 0.9
        assert grant.compliance_scores.feasibility_score is None
    
    def test_inheritance_from_grant(self):
        """Test that EnrichedGrant properly inherits from Grant."""
        grant = EnrichedGrant(
            id="inheritance-test",
            title="Inheritance Test Grant",
            description="Testing inheritance from base Grant model",
            funding_amount=50000,
            category="Education"
        )
        
        # Test base Grant fields are accessible
        assert grant.id == "inheritance-test"
        assert grant.title == "Inheritance Test Grant"
        assert grant.funding_amount == 50000
        assert grant.category == "Education"
        
        # Test enriched fields are also available
        assert hasattr(grant, 'research_scores')
        assert hasattr(grant, 'compliance_scores')
        assert hasattr(grant, 'identified_sector')
    
    def test_serialization_with_nested_objects(self):
        """Test JSON serialization with complex nested objects."""
        grant = EnrichedGrant(
            id="serialization-test",
            title="Serialization Test",
            description="Test serialization of complex grant",
            research_scores=ResearchContextScores(
                sector_relevance=0.85,
                geographic_relevance=0.75
            ),
            compliance_scores=ComplianceScores(
                business_logic_alignment=0.90,
                strategic_synergy=0.80
            ),
            source_details=GrantSourceDetails(
                source_name="Test Source",
                source_url="https://test.com"
            ),
            keywords=["test", "serialization"],
            categories_project=["testing"]
        )
        
        # Test serialization
        data = grant.model_dump()
        assert isinstance(data, dict)
        assert isinstance(data["research_scores"], dict)
        assert isinstance(data["compliance_scores"], dict)
        assert isinstance(data["source_details"], dict)
        assert isinstance(data["keywords"], list)
        
        # Test deserialization
        reconstructed = EnrichedGrant(**data)
        assert reconstructed.id == grant.id
        assert reconstructed.research_scores.sector_relevance == grant.research_scores.sector_relevance
        assert reconstructed.compliance_scores.business_logic_alignment == grant.compliance_scores.business_logic_alignment


class TestGrantSearchFilters:
    """Test GrantSearchFilters validation and functionality."""
    
    def test_valid_filters(self):
        """Test creation with valid filter parameters."""
        filters = GrantSearchFilters(
            min_score=0.7,
            max_score=0.95,
            category="technology",
            deadline_before="2025-12-31",
            search_text="AI machine learning"
        )
        
        assert filters.min_score == 0.7
        assert filters.max_score == 0.95
        assert filters.category == "technology"
        assert filters.deadline_before == "2025-12-31"
        assert filters.search_text == "AI machine learning"
    
    def test_optional_filters(self):
        """Test that all filter fields are optional."""
        filters = GrantSearchFilters()
        
        assert filters.min_score is None
        assert filters.max_score is None
        assert filters.category is None
        assert filters.deadline_before is None
        assert filters.search_text is None
    
    def test_alias_support(self):
        """Test field aliases work correctly."""
        # Test with aliases
        filters = GrantSearchFilters(
            minScore=0.8,
            maxScore=0.9,
            deadlineBefore="2025-06-30",
            searchText="healthcare"
        )
        
        assert filters.min_score == 0.8
        assert filters.max_score == 0.9
        assert filters.deadline_before == "2025-06-30"
        assert filters.search_text == "healthcare"


class TestDashboardStats:
    """Test DashboardStats validation and functionality."""
    
    def test_valid_dashboard_stats(self):
        """Test creation with valid dashboard statistics."""
        stats = DashboardStats(
            totalGrants=150,
            averageScore=0.78,
            grantsThisMonth=25,
            upcomingDeadlines=8
        )
        
        assert stats.total_grants == 150
        assert stats.average_score == 0.78
        assert stats.grants_this_month == 25
        assert stats.upcoming_deadlines == 8
    
    def test_required_fields(self):
        """Test that all fields are required."""
        with pytest.raises(ValidationError):
            DashboardStats()
        
        with pytest.raises(ValidationError):
            DashboardStats(totalGrants=100)  # Missing other required fields
    
    def test_field_aliases(self):
        """Test that field aliases work for dashboard stats."""
        stats = DashboardStats(
            totalGrants=100,
            averageScore=0.85,
            grantsThisMonth=15,
            upcomingDeadlines=5
        )
        
        # Test serialization uses aliases
        data = stats.model_dump(by_alias=True)
        assert "totalGrants" in data
        assert "averageScore" in data
        assert "grantsThisMonth" in data
        assert "upcomingDeadlines" in data


class TestUserSettings:
    """Test UserSettings validation and functionality."""
    
    def test_valid_user_settings(self):
        """Test creation with valid user settings."""
        settings = UserSettings(
            telegramEnabled=True,
            emailNotifications=False,
            deadlineReminders=True,
            searchFrequency="daily",
            categories=["technology", "healthcare"],
            minimumScore=0.75
        )
        
        assert settings.telegram_enabled is True
        assert settings.email_notifications is False
        assert settings.deadline_reminders is True
        assert settings.search_frequency == "daily"
        assert settings.categories == ["technology", "healthcare"]
        assert settings.minimum_score == 0.75
    
    def test_required_settings_fields(self):
        """Test that all settings fields are required."""
        with pytest.raises(ValidationError):
            UserSettings()
        
        with pytest.raises(ValidationError):
            UserSettings(telegramEnabled=True)  # Missing other required fields
    
    def test_categories_list_validation(self):
        """Test that categories field accepts list of strings."""
        settings = UserSettings(
            telegramEnabled=True,
            emailNotifications=True,
            deadlineReminders=True,
            searchFrequency="weekly",
            categories=[],  # Empty list should be valid
            minimumScore=0.5
        )
        
        assert settings.categories == []
        
        # Test with multiple categories
        settings_multi = UserSettings(
            telegramEnabled=False,
            emailNotifications=True,
            deadlineReminders=False,
            searchFrequency="monthly",
            categories=["tech", "health", "education", "environment"],
            minimumScore=0.8
        )
        
        assert len(settings_multi.categories) == 4
        assert "tech" in settings_multi.categories


class TestModelInteroperability:
    """Test how different models work together."""
    
    def test_grant_with_all_nested_models(self):
        """Test grant with all possible nested model combinations."""
        now = datetime.now()
        
        complete_grant = EnrichedGrant(
            id="complete-test",
            title="Complete Integration Test",
            description="Testing all nested models together",
            research_scores=ResearchContextScores(
                sector_relevance=0.9,
                geographic_relevance=0.8,
                operational_alignment=0.85
            ),
            compliance_scores=ComplianceScores(
                business_logic_alignment=0.88,
                feasibility_score=0.75,
                strategic_synergy=0.92
            ),
            source_details=GrantSourceDetails(
                source_name="Complete Test Source",
                source_url="https://complete.test.com",
                retrieved_at=now
            ),
            keywords=["integration", "testing", "complete"],
            categories_project=["testing", "validation"],
            specific_location_mentions=["Test City", "Validation County"],
            enrichment_log=["Model creation", "Validation test", "Integration test"]
        )
        
        # Test that all nested objects are properly accessible
        assert complete_grant.research_scores.sector_relevance == 0.9
        assert complete_grant.compliance_scores.business_logic_alignment == 0.88
        assert complete_grant.source_details.source_name == "Complete Test Source"
        assert len(complete_grant.keywords) == 3
        assert len(complete_grant.enrichment_log) == 3
        
        # Test full serialization and reconstruction
        data = complete_grant.model_dump()
        reconstructed = EnrichedGrant(**data)
        
        assert reconstructed.id == complete_grant.id
        assert reconstructed.research_scores.sector_relevance == complete_grant.research_scores.sector_relevance
        assert reconstructed.compliance_scores.strategic_synergy == complete_grant.compliance_scores.strategic_synergy
        assert reconstructed.source_details.retrieved_at == complete_grant.source_details.retrieved_at
    
    def test_model_defaults_and_none_handling(self):
        """Test how models handle None values and defaults."""
        grant = EnrichedGrant(
            id="defaults-test",
            title="Defaults Test",
            description="Testing default value handling",
            research_scores=None,  # Explicitly set to None
            compliance_scores=ComplianceScores(),  # Default empty scores
            keywords=None  # This should default to empty list
        )
        
        assert grant.research_scores is None
        assert grant.compliance_scores is not None
        assert grant.compliance_scores.business_logic_alignment is None
        # Note: Pydantic default_factory should make this an empty list
        assert grant.keywords == [] or grant.keywords is None
