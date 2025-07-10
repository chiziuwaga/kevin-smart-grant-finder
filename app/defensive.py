"""
Enhanced defensive programming utilities for robust data handling.
"""
import logging
import json
from datetime import datetime
from typing import Any, Optional, List, Dict, Union
from app.schemas import EnrichedGrant, ResearchContextScores, ComplianceScores, GrantSourceDetails
from database.models import Grant as DBGrant

logger = logging.getLogger(__name__)

class SafeDataConverter:
    """Safe data conversion utilities with comprehensive error handling"""
    
    @staticmethod
    def safe_getattr(obj: Any, attr: str, default: Any = None) -> Any:
        """Safely get attribute with None check and logging"""
        try:
            if obj is None:
                return default
            return getattr(obj, attr, default)
        except Exception as e:
            logger.debug(f"Error accessing attribute '{attr}': {e}")
            return default
    
    @staticmethod
    def safe_parse_json(json_field: Any, default: Any = None) -> Any:
        """Safely parse JSON field with comprehensive error handling"""
        if json_field is None:
            return default
        
        try:
            if isinstance(json_field, (dict, list)):
                return json_field
            if isinstance(json_field, str):
                if not json_field.strip():
                    return default
                return json.loads(json_field)
            return default
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            logger.debug(f"Error parsing JSON: {e}")
            return default
    
    @staticmethod
    def safe_float_conversion(value: Any, default: Optional[float] = None) -> Optional[float]:
        """Safely convert value to float"""
        if value is None:
            return default
        
        try:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                # Handle currency symbols and commas
                cleaned = value.replace('$', '').replace(',', '').strip()
                if cleaned:
                    return float(cleaned)
            return default
        except (ValueError, TypeError) as e:
            logger.debug(f"Error converting to float: {e}")
            return default
    
    @staticmethod
    def safe_datetime_conversion(value: Any) -> Optional[datetime]:
        """Safely convert value to datetime"""
        if value is None:
            return None
        
        try:
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                # Try common datetime formats
                formats = [
                    "%Y-%m-%d",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%Y-%m-%dT%H:%M:%S.%fZ",
                    "%m/%d/%Y",
                    "%d/%m/%Y"
                ]
                
                for fmt in formats:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
                
                # Try ISO format parsing
                try:
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    pass
            
            return None
        except Exception as e:
            logger.debug(f"Error converting to datetime: {e}")
            return None
    
    @staticmethod
    def safe_list_conversion(value: Any, default: Optional[List] = None) -> List:
        """Safely convert value to list"""
        if default is None:
            default = []
        
        if value is None:
            return default
        
        try:
            if isinstance(value, list):
                return value
            if isinstance(value, (str, dict)):
                return [value]
            return default
        except Exception as e:
            logger.debug(f"Error converting to list: {e}")
            return default
    
    @staticmethod
    def safe_dict_conversion(value: Any, default: Optional[Dict] = None) -> Dict:
        """Safely convert value to dict"""
        if default is None:
            default = {}
        
        if value is None:
            return default
        
        try:
            if isinstance(value, dict):
                return value
            return default
        except Exception as e:
            logger.debug(f"Error converting to dict: {e}")
            return default

class RobustGrantConverter:
    """Robust converter for database models to Pydantic schemas"""
    
    @staticmethod
    def convert_db_grant_to_enriched(grant_model: DBGrant) -> Optional[EnrichedGrant]:
        """Convert database grant model to EnrichedGrant with comprehensive error handling"""
        try:
            if grant_model is None:
                logger.warning("Received None grant_model in conversion")
                return None
            
            converter = SafeDataConverter()
            
            # Extract basic required fields
            grant_id = converter.safe_getattr(grant_model, 'id')
            if grant_id is None:
                logger.warning("Grant model missing required ID field")
                return None
            
            # Extract scores with safe access
            overall_composite_score = converter.safe_float_conversion(
                converter.safe_getattr(grant_model, 'overall_composite_score'), 0.0
            )
            
            # Safely access analysis data
            analyses = converter.safe_getattr(grant_model, 'analyses', [])
            
            # Build research context scores safely
            research_scores = None
            compliance_scores = None
            
            if analyses and len(analyses) > 0:
                analysis = analyses[0]  # Take the most recent analysis
                
                research_scores = ResearchContextScores(
                    sector_relevance=converter.safe_float_conversion(
                        converter.safe_getattr(analysis, 'sector_relevance_score'), 0.0
                    ),
                    geographic_relevance=converter.safe_float_conversion(
                        converter.safe_getattr(analysis, 'geographic_relevance_score'), 0.0
                    ),
                    operational_alignment=converter.safe_float_conversion(
                        converter.safe_getattr(analysis, 'operational_alignment_score'), 0.0
                    )
                )
                
                compliance_scores = ComplianceScores(
                    business_logic_alignment=converter.safe_float_conversion(
                        converter.safe_getattr(analysis, 'business_logic_alignment_score'), 0.0
                    ),
                    feasibility_score=converter.safe_float_conversion(
                        converter.safe_getattr(analysis, 'feasibility_score'), 0.0
                    ),
                    strategic_synergy=converter.safe_float_conversion(
                        converter.safe_getattr(analysis, 'strategic_synergy_score'), 0.0
                    ),
                    final_weighted_score=converter.safe_float_conversion(
                        converter.safe_getattr(analysis, 'final_score'), 0.0
                    )
                )
            
            # Build source details safely
            source_details = GrantSourceDetails(
                source_name=converter.safe_getattr(grant_model, 'source_name', 'Unknown'),
                source_url=converter.safe_getattr(grant_model, 'source_url', ''),
                retrieved_at=converter.safe_datetime_conversion(
                    converter.safe_getattr(grant_model, 'retrieved_at')
                )
            )
            
            # Parse JSON fields safely
            keywords = converter.safe_list_conversion(
                converter.safe_parse_json(
                    converter.safe_getattr(grant_model, 'keywords_json'), []
                )
            )
            
            categories_project = converter.safe_list_conversion(
                converter.safe_parse_json(
                    converter.safe_getattr(grant_model, 'categories_project_json'), []
                )
            )
            
            specific_location_mentions = converter.safe_list_conversion(
                converter.safe_parse_json(
                    converter.safe_getattr(grant_model, 'specific_location_mentions_json'), []
                )
            )
            
            # Create EnrichedGrant with safe defaults
            enriched_grant = EnrichedGrant(
                # Basic required fields
                id=str(grant_id),
                title=converter.safe_getattr(grant_model, 'title', 'Untitled Grant'),
                description=converter.safe_getattr(grant_model, 'description', 'No description available'),
                
                # Funding information
                funding_amount=converter.safe_float_conversion(
                    converter.safe_getattr(grant_model, 'funding_amount')
                ),
                funding_amount_min=converter.safe_float_conversion(
                    converter.safe_getattr(grant_model, 'funding_amount_min')
                ),
                funding_amount_max=converter.safe_float_conversion(
                    converter.safe_getattr(grant_model, 'funding_amount_max')
                ),
                funding_amount_exact=converter.safe_float_conversion(
                    converter.safe_getattr(grant_model, 'funding_amount_exact')
                ),
                funding_amount_display=converter.safe_getattr(
                    grant_model, 'funding_amount_display', 'Not specified'
                ),
                
                # Dates
                deadline=converter.safe_datetime_conversion(
                    converter.safe_getattr(grant_model, 'deadline')
                ),
                deadline_date=converter.safe_datetime_conversion(
                    converter.safe_getattr(grant_model, 'deadline_date')
                ),
                application_open_date=converter.safe_datetime_conversion(
                    converter.safe_getattr(grant_model, 'application_open_date')
                ),
                
                # Basic fields
                eligibility_criteria=converter.safe_getattr(
                    grant_model, 'eligibility_summary_llm', ''
                ),
                category=converter.safe_getattr(grant_model, 'identified_sector', 'General'),
                source_url=converter.safe_getattr(grant_model, 'source_url', ''),
                source_name=converter.safe_getattr(grant_model, 'source_name', 'Unknown'),
                
                # Enhanced fields
                grant_id_external=converter.safe_getattr(grant_model, 'grant_id_external'),
                summary_llm=converter.safe_getattr(grant_model, 'summary_llm'),
                eligibility_summary_llm=converter.safe_getattr(
                    grant_model, 'eligibility_summary_llm', ''
                ),
                funder_name=converter.safe_getattr(grant_model, 'funder_name'),
                
                # Keywords and categories
                keywords=keywords,
                categories_project=categories_project,
                specific_location_mentions=specific_location_mentions,
                
                # Source details
                source_details=source_details,
                
                # Contextual fields
                identified_sector=converter.safe_getattr(grant_model, 'identified_sector', 'General'),
                identified_sub_sector=converter.safe_getattr(grant_model, 'identified_sub_sector'),
                geographic_scope=converter.safe_getattr(grant_model, 'geographic_scope'),
                
                # Scoring systems
                research_scores=research_scores,
                compliance_scores=compliance_scores,
                overall_composite_score=overall_composite_score,
                
                # Compliance and feasibility
                compliance_summary=converter.safe_dict_conversion(
                    converter.safe_parse_json(
                        converter.safe_getattr(grant_model, 'compliance_summary_json')
                    )
                ),
                feasibility_score=converter.safe_float_conversion(
                    converter.safe_getattr(grant_model, 'feasibility_score')
                ),
                risk_assessment=converter.safe_dict_conversion(
                    converter.safe_parse_json(
                        converter.safe_getattr(grant_model, 'risk_assessment_json')
                    )
                ),
                
                # Additional metadata
                raw_source_data=converter.safe_dict_conversion(
                    converter.safe_parse_json(
                        converter.safe_getattr(grant_model, 'raw_source_data_json')
                    )
                ),
                enrichment_log=converter.safe_list_conversion(
                    converter.safe_parse_json(
                        converter.safe_getattr(grant_model, 'enrichment_log_json'), []
                    )
                )
            )
            
            return enriched_grant
            
        except Exception as e:
            logger.error(f"Error converting grant model to EnrichedGrant: {e}", exc_info=True)
            return None
    
    @staticmethod
    def safe_convert_grant_list(grant_models: List[DBGrant]) -> List[EnrichedGrant]:
        """Safely convert a list of grant models to EnrichedGrant objects"""
        enriched_grants = []
        
        for grant_model in grant_models:
            try:
                enriched_grant = RobustGrantConverter.convert_db_grant_to_enriched(grant_model)
                if enriched_grant:
                    enriched_grants.append(enriched_grant)
                else:
                    logger.warning(f"Failed to convert grant model ID: {getattr(grant_model, 'id', 'unknown')}")
            except Exception as e:
                logger.error(f"Error in grant conversion loop: {e}", exc_info=True)
                continue
        
        return enriched_grants
