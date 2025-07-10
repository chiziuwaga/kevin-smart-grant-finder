"""
Safe model conversion utilities with comprehensive null safety.
Prevents AttributeError and other model conversion issues.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union, TypeVar, Type
from datetime import datetime, date
from decimal import Decimal

from app.schemas import (
    EnrichedGrant, 
    ResearchContextScores, 
    ComplianceScores, 
    GrantSourceDetails
)
from database.models import Grant as DBGrant, Analysis

logger = logging.getLogger(__name__)

T = TypeVar('T')

class SafeModelConverter:
    """Utility class for safe model conversion with comprehensive error handling"""
    
    @staticmethod
    def safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
        """Safely get attribute with None check and type validation"""
        try:
            if obj is None:
                return default
            
            value = getattr(obj, attr, default)
            return value if value is not None else default
            
        except (AttributeError, TypeError) as e:
            logger.debug(f"Safe getattr failed for {attr}: {e}")
            return default
    
    @staticmethod
    def safe_parse_json(json_field: Any, default: Any = None) -> Any:
        """Safely parse JSON field with comprehensive error handling"""
        if json_field is None:
            return default
        
        # If already parsed (dict/list), return as-is
        if isinstance(json_field, (dict, list)):
            return json_field
        
        # If string, try to parse
        if isinstance(json_field, str):
            if not json_field.strip():
                return default
            
            try:
                parsed = json.loads(json_field)
                return parsed if parsed is not None else default
            except (json.JSONDecodeError, TypeError) as e:
                logger.debug(f"JSON parse failed: {e}")
                return default
        
        # For other types, return default
        return default
    
    @staticmethod
    def safe_datetime_conversion(dt_value: Any) -> Optional[datetime]:
        """Safely convert various datetime formats"""
        if dt_value is None:
            return None
        
        # Already a datetime
        if isinstance(dt_value, datetime):
            return dt_value
        
        # Date object
        if isinstance(dt_value, date):
            return datetime.combine(dt_value, datetime.min.time())
        
        # String conversion
        if isinstance(dt_value, str):
            if not dt_value.strip():
                return None
            
            # Try common formats
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%d"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(dt_value, fmt)
                except ValueError:
                    continue
            
            # Try ISO format
            try:
                return datetime.fromisoformat(dt_value.replace('Z', '+00:00'))
            except ValueError:
                logger.debug(f"Could not parse datetime: {dt_value}")
                return None
        
        return None
    
    @staticmethod
    def safe_float_conversion(value: Any) -> Optional[float]:
        """Safely convert value to float"""
        if value is None:
            return None
        
        if isinstance(value, (int, float, Decimal)):
            return float(value)
        
        if isinstance(value, str):
            if not value.strip():
                return None
            
            try:
                # Remove common formatting
                clean_value = value.replace(',', '').replace('$', '').strip()
                return float(clean_value)
            except (ValueError, TypeError):
                logger.debug(f"Could not convert to float: {value}")
                return None
        
        return None
    
    @staticmethod
    def safe_int_conversion(value: Any) -> Optional[int]:
        """Safely convert value to int"""
        if value is None:
            return None
        
        if isinstance(value, int):
            return value
        
        if isinstance(value, (float, Decimal)):
            return int(value)
        
        if isinstance(value, str):
            if not value.strip():
                return None
            
            try:
                clean_value = value.replace(',', '').replace('$', '').strip()
                return int(float(clean_value))
            except (ValueError, TypeError):
                logger.debug(f"Could not convert to int: {value}")
                return None
        
        return None
    
    @staticmethod
    def safe_list_conversion(value: Any, default: Optional[List] = None) -> List[Any]:
        """Safely convert value to list"""
        if default is None:
            default = []
        
        if value is None:
            return default
        
        if isinstance(value, list):
            return value
        
        if isinstance(value, (tuple, set)):
            return list(value)
        
        if isinstance(value, str):
            if not value.strip():
                return default
            
            # Try to parse as JSON array
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
            
            # Split by common delimiters
            for delimiter in [',', ';', '|']:
                if delimiter in value:
                    return [item.strip() for item in value.split(delimiter) if item.strip()]
            
            # Single item
            return [value.strip()]
        
        return default
    
    @staticmethod
    def safe_dict_conversion(value: Any, default: Optional[Dict] = None) -> Dict[str, Any]:
        """Safely convert value to dict"""
        if default is None:
            default = {}
        
        if value is None:
            return default
        
        if isinstance(value, dict):
            return value
        
        if isinstance(value, str):
            if not value.strip():
                return default
            
            try:
                parsed = json.loads(value)
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
        
        return default
    
    @staticmethod
    def safe_string_conversion(value: Any, default: str = "") -> str:
        """Safely convert value to string"""
        if value is None:
            return default
        
        if isinstance(value, str):
            return value.strip()
        
        try:
            return str(value).strip()
        except Exception:
            return default

class EnhancedGrantConverter(SafeModelConverter):
    """Enhanced grant model converter with comprehensive safety checks"""
    
    @classmethod
    def convert_db_grant_to_enriched(cls, grant_model: Optional[DBGrant]) -> Optional[EnrichedGrant]:
        """
        Convert database grant model to EnrichedGrant with comprehensive safety checks.
        Returns None if conversion fails rather than raising exceptions.
        """
        try:
            if grant_model is None:
                logger.warning("Received None grant_model in conversion")
                return None
            
            # Validate required fields
            grant_id = cls.safe_getattr(grant_model, 'id')
            if grant_id is None:
                logger.warning("Grant model missing required ID field")
                return None
            
            # Extract basic fields with safe defaults
            title = cls.safe_string_conversion(cls.safe_getattr(grant_model, 'title'), 'Untitled Grant')
            description = cls.safe_string_conversion(cls.safe_getattr(grant_model, 'description'), 'No description available')
            
            # Extract funding information
            funding_amount = cls.safe_float_conversion(cls.safe_getattr(grant_model, 'funding_amount'))
            funding_amount_min = cls.safe_float_conversion(cls.safe_getattr(grant_model, 'funding_amount_min'))
            funding_amount_max = cls.safe_float_conversion(cls.safe_getattr(grant_model, 'funding_amount_max'))
            funding_amount_exact = cls.safe_float_conversion(cls.safe_getattr(grant_model, 'funding_amount_exact'))
            funding_amount_display = cls.safe_string_conversion(
                cls.safe_getattr(grant_model, 'funding_amount_display'), 
                'Not specified'
            )
            
            # Extract dates
            deadline = cls.safe_datetime_conversion(cls.safe_getattr(grant_model, 'deadline'))
            deadline_date = cls.safe_datetime_conversion(cls.safe_getattr(grant_model, 'deadline_date'))
            application_open_date = cls.safe_datetime_conversion(cls.safe_getattr(grant_model, 'application_open_date'))
            
            # Extract categorization
            category = cls.safe_string_conversion(cls.safe_getattr(grant_model, 'identified_sector'), 'General')
            identified_sector = cls.safe_string_conversion(cls.safe_getattr(grant_model, 'identified_sector'), 'General')
            identified_sub_sector = cls.safe_string_conversion(cls.safe_getattr(grant_model, 'identified_sub_sector'))
            geographic_scope = cls.safe_string_conversion(cls.safe_getattr(grant_model, 'geographic_scope'))
            
            # Extract source information
            source_url = cls.safe_string_conversion(cls.safe_getattr(grant_model, 'source_url'))
            source_name = cls.safe_string_conversion(cls.safe_getattr(grant_model, 'source_name'), 'Unknown')
            funder_name = cls.safe_string_conversion(cls.safe_getattr(grant_model, 'funder_name'))
            grant_id_external = cls.safe_string_conversion(cls.safe_getattr(grant_model, 'grant_id_external'))
            
            # Extract LLM-generated content
            summary_llm = cls.safe_string_conversion(cls.safe_getattr(grant_model, 'summary_llm'))
            eligibility_summary_llm = cls.safe_string_conversion(cls.safe_getattr(grant_model, 'eligibility_summary_llm'))
            
            # Extract lists and JSON fields
            keywords = cls.safe_list_conversion(
                cls.safe_parse_json(cls.safe_getattr(grant_model, 'keywords_json'), [])
            )
            categories_project = cls.safe_list_conversion(
                cls.safe_parse_json(cls.safe_getattr(grant_model, 'categories_project_json'), [])
            )
            specific_location_mentions = cls.safe_list_conversion(
                cls.safe_parse_json(cls.safe_getattr(grant_model, 'specific_location_mentions_json'), [])
            )
            
            # Extract complex JSON fields
            compliance_summary = cls.safe_dict_conversion(
                cls.safe_parse_json(cls.safe_getattr(grant_model, 'compliance_summary_json'))
            )
            risk_assessment = cls.safe_dict_conversion(
                cls.safe_parse_json(cls.safe_getattr(grant_model, 'risk_assessment_json'))
            )
            raw_source_data = cls.safe_dict_conversion(
                cls.safe_parse_json(cls.safe_getattr(grant_model, 'raw_source_data_json'))
            )
            enrichment_log = cls.safe_list_conversion(
                cls.safe_parse_json(cls.safe_getattr(grant_model, 'enrichment_log_json'), [])
            )
            
            # Extract scoring information
            overall_composite_score = cls.safe_float_conversion(cls.safe_getattr(grant_model, 'overall_composite_score'))
            feasibility_score = cls.safe_float_conversion(cls.safe_getattr(grant_model, 'feasibility_score'))
            
            # Build source details
            source_details = None
            if source_name or source_url:
                source_details = GrantSourceDetails(
                    source_name=source_name,
                    source_url=source_url,
                    retrieved_at=cls.safe_datetime_conversion(cls.safe_getattr(grant_model, 'retrieved_at'))
                )
            
            # Extract analysis data safely
            research_scores, compliance_scores = cls._extract_analysis_scores(grant_model)
            
            # Create EnrichedGrant with all safety checks
            enriched_grant = EnrichedGrant(
                # Basic identification
                id=str(grant_id),
                title=title,
                description=description,
                
                # Funding information
                funding_amount=funding_amount,
                funding_amount_min=funding_amount_min,
                funding_amount_max=funding_amount_max,
                funding_amount_exact=funding_amount_exact,
                funding_amount_display=funding_amount_display,
                
                # Dates
                deadline=deadline,
                deadline_date=deadline_date,
                application_open_date=application_open_date,
                
                # Categorization
                eligibility_criteria=eligibility_summary_llm,
                category=category,
                identified_sector=identified_sector,
                identified_sub_sector=identified_sub_sector,
                geographic_scope=geographic_scope,
                
                # Source information
                source_url=source_url,
                source_name=source_name,
                funder_name=funder_name,
                grant_id_external=grant_id_external,
                
                # LLM content
                summary_llm=summary_llm,
                eligibility_summary_llm=eligibility_summary_llm,
                
                # Lists and arrays
                keywords=keywords,
                categories_project=categories_project,
                specific_location_mentions=specific_location_mentions,
                
                # Complex objects
                source_details=source_details,
                research_scores=research_scores,
                compliance_scores=compliance_scores,
                
                # Scoring
                overall_composite_score=overall_composite_score,
                feasibility_score=feasibility_score,
                
                # JSON fields
                compliance_summary=compliance_summary,
                risk_assessment=risk_assessment,
                raw_source_data=raw_source_data,
                enrichment_log=enrichment_log
            )
            
            logger.debug(f"Successfully converted grant {grant_id} to EnrichedGrant")
            return enriched_grant
            
        except Exception as e:
            logger.error(f"Error converting grant model to EnrichedGrant: {e}", exc_info=True)
            return None
    
    @classmethod
    def _extract_analysis_scores(cls, grant_model: DBGrant) -> tuple[Optional[ResearchContextScores], Optional[ComplianceScores]]:
        """Extract analysis scores from grant model safely"""
        research_scores = None
        compliance_scores = None
        
        try:
            analyses = cls.safe_getattr(grant_model, 'analyses', [])
            if not analyses:
                return research_scores, compliance_scores
            
            # Get the most recent analysis
            latest_analysis = None
            if isinstance(analyses, list) and len(analyses) > 0:
                # Sort by created_at if available, otherwise take first
                try:
                    latest_analysis = max(
                        analyses, 
                        key=lambda a: cls.safe_getattr(a, 'created_at', datetime.min) or datetime.min
                    )
                except (ValueError, TypeError):
                    latest_analysis = analyses[0]
            
            if latest_analysis:
                # Build research context scores
                research_scores = ResearchContextScores(
                    sector_relevance=cls.safe_float_conversion(
                        cls.safe_getattr(latest_analysis, 'sector_relevance_score', 0.0)
                    ),
                    geographic_relevance=cls.safe_float_conversion(
                        cls.safe_getattr(latest_analysis, 'geographic_relevance_score', 0.0)
                    ),
                    operational_alignment=cls.safe_float_conversion(
                        cls.safe_getattr(latest_analysis, 'operational_alignment_score', 0.0)
                    )
                )
                
                # Build compliance scores
                compliance_scores = ComplianceScores(
                    business_logic_alignment=cls.safe_float_conversion(
                        cls.safe_getattr(latest_analysis, 'business_logic_alignment_score', 0.0)
                    ),
                    feasibility_score=cls.safe_float_conversion(
                        cls.safe_getattr(latest_analysis, 'feasibility_score', 0.0)
                    ),
                    strategic_synergy=cls.safe_float_conversion(
                        cls.safe_getattr(latest_analysis, 'strategic_synergy_score', 0.0)
                    ),
                    final_weighted_score=cls.safe_float_conversion(
                        cls.safe_getattr(latest_analysis, 'final_score', 0.0)
                    )
                )
        
        except Exception as e:
            logger.debug(f"Error extracting analysis scores: {e}")
        
        return research_scores, compliance_scores
    
    @classmethod
    def convert_enriched_to_db_grant(cls, enriched_grant: EnrichedGrant) -> Dict[str, Any]:
        """
        Convert EnrichedGrant back to database grant data.
        Returns dictionary suitable for database operations.
        """
        try:
            db_data = {
                # Basic fields
                'title': enriched_grant.title,
                'description': enriched_grant.description,
                
                # Funding
                'funding_amount': enriched_grant.funding_amount,
                'funding_amount_min': enriched_grant.funding_amount_min,
                'funding_amount_max': enriched_grant.funding_amount_max,
                'funding_amount_exact': enriched_grant.funding_amount_exact,
                'funding_amount_display': enriched_grant.funding_amount_display,
                
                # Dates
                'deadline': enriched_grant.deadline,
                'deadline_date': enriched_grant.deadline_date,
                'application_open_date': enriched_grant.application_open_date,
                
                # Categorization
                'identified_sector': enriched_grant.identified_sector,
                'identified_sub_sector': enriched_grant.identified_sub_sector,
                'geographic_scope': enriched_grant.geographic_scope,
                
                # Source
                'source_url': enriched_grant.source_url,
                'source_name': enriched_grant.source_name,
                'funder_name': enriched_grant.funder_name,
                'grant_id_external': enriched_grant.grant_id_external,
                
                # LLM content
                'summary_llm': enriched_grant.summary_llm,
                'eligibility_summary_llm': enriched_grant.eligibility_summary_llm,
                
                # Scoring
                'overall_composite_score': enriched_grant.overall_composite_score,
                'feasibility_score': enriched_grant.feasibility_score,
                
                # JSON fields - safely serialize
                'keywords_json': json.dumps(enriched_grant.keywords) if enriched_grant.keywords else None,
                'categories_project_json': json.dumps(enriched_grant.categories_project) if enriched_grant.categories_project else None,
                'specific_location_mentions_json': json.dumps(enriched_grant.specific_location_mentions) if enriched_grant.specific_location_mentions else None,
                'compliance_summary_json': json.dumps(enriched_grant.compliance_summary) if enriched_grant.compliance_summary else None,
                'risk_assessment_json': json.dumps(enriched_grant.risk_assessment) if enriched_grant.risk_assessment else None,
                'raw_source_data_json': json.dumps(enriched_grant.raw_source_data) if enriched_grant.raw_source_data else None,
                'enrichment_log_json': json.dumps(enriched_grant.enrichment_log) if enriched_grant.enrichment_log else None,
                
                # Source details
                'retrieved_at': enriched_grant.source_details.retrieved_at if enriched_grant.source_details else None
            }
            
            # Filter out None values for cleaner database operations
            return {k: v for k, v in db_data.items() if v is not None}
            
        except Exception as e:
            logger.error(f"Error converting EnrichedGrant to database format: {e}", exc_info=True)
            return {}

# Convenience functions for easy usage
def convert_db_grant_safely(grant_model: Optional[DBGrant]) -> Optional[EnrichedGrant]:
    """Convenience function for safe grant conversion"""
    return EnhancedGrantConverter.convert_db_grant_to_enriched(grant_model)

def convert_enriched_grant_to_db(enriched_grant: EnrichedGrant) -> Dict[str, Any]:
    """Convenience function for converting enriched grant to database format"""
    return EnhancedGrantConverter.convert_enriched_to_db_grant(enriched_grant)
