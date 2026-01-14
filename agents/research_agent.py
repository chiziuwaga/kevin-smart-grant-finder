"""
Research Agent for finding grant opportunities.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import yaml
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.models import GrantFilter
from app.schemas import EnrichedGrant
from services.deepseek_client import DeepSeekClient

logger = logging.getLogger(__name__)

class ResearchAgent:
    """
    This class is being deprecated in favor of the more robust
    `RecursiveResearchAgent` and `IntegratedResearchAgent`.
    The logic here for tiered search and deep research is being replaced
    by a recursive, chunked reasoning approach.
    """

    def __init__(
        self,
        db_session_maker: async_sessionmaker,
        deepseek_client: Optional[DeepSeekClient] = None,
        config_path: str = "config"
    ):
        """Initialize Research Agent with configuration loading."""
        logger.warning("The `ResearchAgent` is deprecated and will be removed in a future version. "
                       "Please use `IntegratedResearchAgent` instead.")

        if not deepseek_client:
            raise ValueError("DeepSeek client cannot be None.")
        if not db_session_maker:
            raise ValueError("Database session maker cannot be None.")

        self.db_session_maker = db_session_maker
        self.deepseek_client = deepseek_client
        self.config_path = Path(config_path)
        self.logger = logging.getLogger(__name__)

        self.sector_config: Dict[str, Any] = {}
        self.geographic_config: Dict[str, Any] = {}
        self.kevin_profile_config: Dict[str, Any] = {}
        self.grant_sources_config: Dict[str, Any] = {}

        self.load_all_configs()

    def load_all_configs(self):
        """Load all necessary configuration files."""
        try:
            self.sector_config = self._load_config("sector_config.yaml")
            self.geographic_config = self._load_config("geographic_config.yaml")
            self.kevin_profile_config = self._load_config("kevin_profile_config.yaml")
            self.grant_sources_config = self._load_config("grant_sources.yaml")
            self.logger.info("Successfully loaded all configuration files for deprecated ResearchAgent")
        except Exception as e:
            self.logger.error(f"Error loading configurations for deprecated agent: {e}", exc_info=True)

    def _load_config(self, filename: str) -> Dict[str, Any]:
        file_path = self.config_path / filename
        if not file_path.is_file():
            raise FileNotFoundError(f"Config file not found: {file_path}")
        with open(file_path, 'r') as file:
            return yaml.safe_load(file)

    async def search_grants(self, grant_filter: Dict[str, Any] | GrantFilter) -> List[EnrichedGrant]:
        """
        This search method is deprecated. The new recursive search logic is
        handled by `IntegratedResearchAgent`.
        """
        logger.warning("`search_grants` in `ResearchAgent` is deprecated. Returning empty list.")
        return []

    # All other methods in this class are now considered obsolete and have been removed.