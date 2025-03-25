import os
import logging
from datetime import datetime
from typing import List, Dict

from database.mongodb_client import MongoDBClient
from database.pinecone_client import PineconeClient
from utils.scrapers.louisiana_scraper import LouisianaGrantScraper
from utils.api_handlers.perplexity_handler import PerplexityRateLimitHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GrantSearchJob:
    def __init__(self):
        """Initialize grant search job with necessary clients."""
        self.mongodb_client = MongoDBClient()
        self.pinecone_client = PineconeClient()
        self.la_scraper = LouisianaGrantScraper()
        self.perplexity_handler = PerplexityRateLimitHandler()
        
    async def _process_grants(self, grants: List[Dict]) -> List[Dict]:
        """Process grants through relevance scoring and filtering.

        Args:
            grants (List[Dict]): Raw grant data.

        Returns:
            List[Dict]: Processed grants with relevance scores.
        """
        processed_grants = []
        
        for grant in grants:
            try:
                # Calculate relevance score
                description = grant.get('description', '')
                if not description:
                    continue
                    
                score = self.pinecone_client.calculate_relevance(description)
                grant['score'] = score
                
                # Only keep grants with sufficient relevance
                if score >= 0.7:  # minimum threshold
                    processed_grants.append(grant)
                    
            except Exception as e:
                logger.error(f"Error processing grant: {e}")
                continue
                
        return processed_grants

    async def run(self):
        """Execute the grant search job."""
        try:
            start_time = datetime.now()
            logger.info("Starting grant search job")
            
            # Scrape Louisiana grants
            la_grants = self.la_scraper.scrape_grants()
            logger.info(f"Found {len(la_grants)} Louisiana grants")
            
            # Process grants
            processed_grants = await self._process_grants(la_grants)
            logger.info(f"Processed {len(processed_grants)} relevant grants")
            
            # Store in MongoDB
            stored_count = self.mongodb_client.store_grants(processed_grants)
            logger.info(f"Stored {stored_count} grants in database")
            
            # Log completion
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"Completed grant search job in {duration:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error in grant search job: {e}")
            raise

def main():
    """Main entry point for the grant search job."""
    try:
        job = GrantSearchJob()
        await job.run()
    except Exception as e:
        logger.error(f"Failed to run grant search job: {e}")
        raise

if __name__ == "__main__":
    main()