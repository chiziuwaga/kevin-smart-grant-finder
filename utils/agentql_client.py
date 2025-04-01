import os
import logging
import requests
import json
import time
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

logger = logging.getLogger(__name__)

class AgentQLClient:
    def __init__(self):
        """Initialize AgentQL client for advanced search capabilities."""
        self.api_key = os.getenv("AGENTQL_API_KEY")
        if not self.api_key:
            # Log an error but don't raise immediately, allow fallback if possible
            logger.error("AgentQL API key not found in environment variables. AgentQL searches will fail.")
            self.base_url = None
            self.headers = {}
            return
            # raise ValueError("AgentQL API key not found in environment variables")

        self.base_url = "https://api.agentql.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        logger.info("AgentQL client initialized")

    def is_available(self):
        """Check if the client was initialized correctly."""
        return bool(self.api_key and self.base_url)

    def create_search_agent(self, name, description, sources):
        """Create a new search agent with specified parameters."""
        if not self.is_available():
            logger.warning("AgentQL client not available. Cannot create agent.")
            return None
        try:
            payload = {
                "name": name,
                "description": description,
                "sources": sources, # List of domain names or URLs
                "capabilities": [
                    "web_search",
                    "website_extraction",
                    "data_transformation"
                ]
            }

            response = requests.post(
                f"{self.base_url}/agents",
                headers=self.headers,
                json=payload,
                timeout=30 # Added timeout
            )
            response.raise_for_status()

            agent_data = response.json()
            agent_id = agent_data.get("agent_id")
            if agent_id:
                logger.info(f"Created/retrieved AgentQL search agent '{name}' with ID: {agent_id}")
                return agent_id
            else:
                 logger.error(f"Failed to get agent_id for AgentQL agent '{name}'. Response: {agent_data}")
                 return None

        except requests.exceptions.HTTPError as e:
            # AgentQL might return 409 if agent name already exists, try to fetch it
            if e.response.status_code == 409:
                 logger.warning(f"AgentQL agent '{name}' likely already exists. Attempting to retrieve ID.")
                 # Add logic here to list agents and find by name if API supports it
                 # For now, just log and return None or handle based on specific API behavior
                 logger.error(f"Agent creation conflict for '{name}'. Manual check might be needed. Error: {e.response.text}")
                 return None # Or retrieve existing ID if possible
            else:
                 logger.error(f"HTTP error creating AgentQL search agent '{name}': {e.response.status_code} - {e.response.text}")
                 return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error creating AgentQL search agent '{name}': {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating AgentQL search agent '{name}': {str(e)}", exc_info=True)
            return None

    def search_grants(self, agent_id, query, parameters=None):
        """Execute a grant search using the specified AgentQL agent."""
        if not self.is_available():
            logger.warning("AgentQL client not available. Cannot search.")
            return []
        if not agent_id:
            logger.error("AgentQL agent ID is required for searching.")
            return []
        try:
            payload = {
                "agent_id": agent_id,
                "query": query,
                "parameters": parameters or {},
                "response_format": "json",
                "max_tokens": 2000
            }

            # Start search
            logger.debug(f"Starting AgentQL search with agent {agent_id} and query: {query}")
            response = requests.post(
                f"{self.base_url}/search",
                headers=self.headers,
                json=payload,
                timeout=30 # Initial request timeout
            )
            response.raise_for_status()

            search_data = response.json()
            search_id = search_data.get("search_id")

            if not search_id:
                logger.error(f"No search ID returned from AgentQL for agent {agent_id}")
                return []

            logger.info(f"AgentQL search initiated with ID: {search_id}")

            # Poll for search results
            max_retries = 30 # ~5-10 minutes total polling time with backoff
            poll_interval = 5 # Initial poll interval in seconds

            for i in range(max_retries):
                time.sleep(poll_interval) # Wait before polling

                logger.debug(f"Polling AgentQL search status for ID: {search_id} (Attempt {i+1})")
                status_response = requests.get(
                    f"{self.base_url}/search/{search_id}",
                    headers=self.headers,
                    timeout=30 # Poll request timeout
                )
                status_response.raise_for_status()

                status_data = status_response.json()
                status = status_data.get("status")

                if status == "completed":
                    results = status_data.get("results", [])
                    # AgentQL results might be nested, adjust based on actual API response
                    processed_results = self._process_search_results(results)
                    logger.info(f"AgentQL search {search_id} completed with {len(processed_results)} processed results.")
                    return processed_results

                elif status == "failed":
                    error = status_data.get("error", "Unknown error")
                    logger.error(f"AgentQL search {search_id} failed: {error}")
                    return []

                elif status == "pending" or status == "running":
                     # Increase poll interval slightly for longer searches
                     poll_interval = min(poll_interval + 2, 30)
                     continue # Continue polling

                else:
                     logger.warning(f"Unknown AgentQL search status '{status}' for ID: {search_id}")
                     # Decide whether to continue polling or break

            logger.warning(f"AgentQL search {search_id} timed out after {max_retries} polling attempts.")
            return []

        except requests.exceptions.HTTPError as e:
             logger.error(f"HTTP error during AgentQL search: {e.response.status_code} - {e.response.text}")
             return []
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error executing AgentQL search: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error executing AgentQL search: {str(e)}", exc_info=True)
            return []

    def _process_search_results(self, results):
        """Process raw search results into structured grant data."""
        grants = []
        if not isinstance(results, list):
             logger.warning(f"Unexpected AgentQL results format: {type(results)}. Expected list.")
             return []

        for result in results:
            try:
                # Adapt based on actual AgentQL response structure
                grant_data = {}

                # Basic grant information
                grant_data["title"] = result.get("title") or result.get("name", "Unknown Grant")
                grant_data["description"] = result.get("description") or result.get("summary") or result.get("content", "No description available")
                grant_data["source_url"] = result.get("url") or result.get("source_url")
                grant_data["source_name"] = result.get("source_name") or self._extract_source_name(grant_data["source_url"])

                # Extract metadata if available (may need adjustment)
                metadata = result.get("metadata", {})
                grant_data["deadline"] = metadata.get("deadline") or result.get("deadline")
                grant_data["amount"] = metadata.get("amount") or metadata.get("funding_amount") or result.get("amount")
                grant_data["eligibility"] = metadata.get("eligibility") or result.get("eligibility")

                # Basic validation
                if grant_data["title"] and grant_data["description"] and grant_data["source_url"]:
                    grants.append(grant_data)
                else:
                    logger.debug(f"Skipping incomplete AgentQL result: {result}")

            except Exception as e:
                logger.error(f"Error processing individual AgentQL search result: {str(e)} - Result: {result}", exc_info=True)

        logger.info(f"Processed {len(grants)} potential grants from AgentQL results.")
        return grants

    def _extract_source_name(self, url):
        """Extract source name from URL."""
        try:
            if not url:
                return "Unknown Source"

            domain = urlparse(url).netloc

            # Remove www. prefix if present
            domain = domain.replace("www.", "")

            # Basic name extraction (can be improved)
            parts = domain.split('.')
            if len(parts) >= 2:
                # Simple heuristic: use the part before the TLD (e.g., 'grants' from 'grants.gov')
                name = parts[-2]
                # Capitalize common abbreviations
                if name.lower() in ['gov', 'org', 'com', 'edu']:
                     return name.upper()
                return name.capitalize()
            else:
                return domain.capitalize() if domain else "Unknown Source"

        except Exception:
            return "Unknown Source"

