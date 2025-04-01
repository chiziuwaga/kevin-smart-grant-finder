import logging
import openai
import os
from dotenv import load_dotenv

# Import client dependencies
from database.pinecone_client import PineconeClient
from database.mongodb_client import MongoDBClient

load_dotenv()

logger = logging.getLogger(__name__)

class AnalysisAgent:
    def __init__(self, pinecone_client: PineconeClient, mongodb_client: MongoDBClient):
        """Initialize Analysis Agent with Pinecone and MongoDB clients."""
        self.pinecone_client = pinecone_client
        self.mongodb_client = mongodb_client

        # Initialize OpenAI client for generating summaries
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.error("OpenAI API key not found in environment variables. Grant summary generation disabled.")
            self.openai_client = None
            # raise ValueError("OpenAI API key not found in environment variables")
        else:
            try:
                 self.openai_client = openai.OpenAI(api_key=openai_api_key)
                 logger.info("OpenAI client initialized for Analysis Agent.")
            except Exception as e:
                 logger.error(f"Failed to initialize OpenAI client: {e}")
                 self.openai_client = None

        # Load relevance threshold from environment
        try:
            self.relevance_threshold = float(os.getenv("RELEVANCE_THRESHOLD", "85"))
        except ValueError:
             logger.warning("Invalid RELEVANCE_THRESHOLD in .env, defaulting to 85.")
             self.relevance_threshold = 85.0

        logger.info(f"Analysis Agent initialized. Relevance threshold: {self.relevance_threshold}%")

    def load_and_store_priorities(self):
        """Load priorities from DB and ensure they are vectorized in Pinecone."""
        priorities = self.mongodb_client.get_priorities()
        if not priorities:
            logger.warning("No priorities found in database. Relevance ranking may be inaccurate.")
            return False
        
        if not self.pinecone_client or not self.pinecone_client.index:
             logger.error("Pinecone client not available. Cannot store priority vectors.")
             return False

        try:
            # Check if priorities need updating in Pinecone (e.g., based on timestamp or hash)
            # For simplicity now, always store/update on startup or before ranking
            logger.info("Storing/updating priority vectors in Pinecone...")
            stored_count = self.pinecone_client.store_priority_vectors(priorities)
            logger.info(f"Stored {stored_count} priority vectors.")
            return True
        except Exception as e:
             logger.error(f"Error storing priority vectors in Pinecone: {e}", exc_info=True)
             return False

    def rank_and_summarize_grants(self, grants: list):
        """Calculate relevance scores, rank grants, and generate summaries for high-priority ones."""
        if not grants:
            logger.info("No grants provided for ranking.")
            return []
        
        if not self.pinecone_client or not self.pinecone_client.index:
             logger.error("Pinecone client not available. Cannot calculate relevance scores.")
             # Return grants unsorted or with default score?
             for grant in grants:
                  grant['relevance_score'] = 0.0
                  grant['summary'] = "Ranking unavailable."
             return grants

        logger.info(f"Ranking {len(grants)} grants...")

        # Ensure priorities are loaded in Pinecone before ranking
        # Consider doing this less frequently if priorities don't change often
        self.load_and_store_priorities()

        ranked_grants = []
        for grant in grants:
            try:
                # Create combined text for relevance calculation
                combined_text = f"Title: {grant.get('title', '')}\n"
                combined_text += f"Description: {grant.get('description', '')}\n"
                if grant.get('eligibility'):
                    combined_text += f"Eligibility: {grant['eligibility']}\n"
                if grant.get('amount'):
                    combined_text += f"Amount: {grant['amount']}\n"

                # Calculate relevance score using Pinecone
                relevance_score = self.pinecone_client.calculate_relevance(
                    grant_description=grant.get('description', ''),
                    grant_title=grant.get('title'),
                    grant_eligibility=grant.get('eligibility')
                )
                grant["relevance_score"] = relevance_score

                # Generate summary for high-relevance grants if OpenAI client is available
                if relevance_score >= self.relevance_threshold and self.openai_client:
                    grant["summary"] = self.generate_grant_summary(grant)
                elif relevance_score >= self.relevance_threshold:
                     grant["summary"] = "Summary generation disabled (OpenAI client unavailable)."
                else:
                     grant["summary"] = None # No summary needed for lower-ranked grants
                
                ranked_grants.append(grant)

            except Exception as e:
                logger.error(f"Error ranking/summarizing grant '{grant.get('title')}': {e}", exc_info=True)
                grant["relevance_score"] = 0.0 # Assign default score on error
                grant["summary"] = "Error during analysis."
                ranked_grants.append(grant) # Still include the grant

        # Sort grants by relevance score (descending)
        sorted_grants = sorted(ranked_grants, key=lambda x: x.get('relevance_score', 0), reverse=True)
        logger.info(f"Ranking complete. Top grant: '{sorted_grants[0].get('title')}' (Score: {sorted_grants[0].get('relevance_score')})")
        return sorted_grants

    def generate_grant_summary(self, grant):
        """Generate a concise summary of a grant opportunity using OpenAI."""
        if not self.openai_client:
            return "Summary generation disabled."

        try:
            # Prepare prompt for summary generation
            deadline_str = "N/A"
            if isinstance(grant.get('deadline'), datetime):
                deadline_str = grant['deadline'].strftime('%B %d, %Y')
            elif grant.get('deadline'): # Handle if it's already a string
                 deadline_str = str(grant['deadline'])

            prompt = f"""
            Create a concise summary (around 100-150 words) of the following grant opportunity.
            Highlight the main purpose, key eligibility criteria, funding amount range (if known), and the deadline.
            Focus on actionable information for a potential applicant.

            Grant Title: {grant.get('title', 'N/A')}
            Description: {grant.get('description', 'N/A')}
            Eligibility: {grant.get('eligibility', 'N/A')}
            Funding Amount: {grant.get('amount', 'N/A')}
            Deadline: {deadline_str}
            Source: {grant.get('source_name', 'N/A')}
            """

            logger.debug(f"Generating summary for grant: {grant.get('title')}")
            # Generate summary using OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo", # Use a cost-effective model for summaries
                messages=[
                    {"role": "system", "content": "You are a helpful assistant specializing in summarizing grant opportunities clearly and concisely."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200, # Limit summary length
                temperature=0.5 # Control creativity
            )

            summary = response.choices[0].message.content.strip()
            logger.debug(f"Generated summary: {summary[:100]}...")
            return summary

        except Exception as e:
            logger.error(f"Error generating grant summary for '{grant.get('title')}': {str(e)}", exc_info=True)
            return "Summary generation failed. Please review the full grant description."
