import os
import logging
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv()

class AgentQLClient:
    def __init__(self, use_mock=True):
        """Initialize AgentQL client for advanced search capabilities."""
        if use_mock:
            self._setup_mock_data()
            logging.info("Using mock AgentQL for development")
            return
            
        self.api_key = os.getenv("AGENTQL_API_KEY")
        if not self.api_key:
            raise ValueError("AgentQL API key not found in environment variables")
        
        self.base_url = "https://api.agentql.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        logging.info("AgentQL client initialized")
    
    def _setup_mock_data(self):
        """Set up mock data for development."""
        self.mock_agent_id = "mock-agent-123"
        self.mock_grants = [
            {
                "title": "USDA Telecommunications Infrastructure Loan",
                "description": "Provides financing for telephone and broadband infrastructure in rural areas.",
                "amount": "$1,000,000+",
                "deadline": "2025-06-30",
                "source": "USDA",
                "source_url": "https://www.rd.usda.gov/programs-services/telecommunications-programs/telecommunications-infrastructure-loans-loan-guarantees",
                "category": "telecom"
            },
            {
                "title": "Women's Business Center Grant",
                "description": "Funding for nonprofit organizations to provide business development assistance to women entrepreneurs.",
                "amount": "$150,000",
                "deadline": "2025-05-15",
                "source": "SBA",
                "source_url": "https://www.sba.gov/local-assistance/resource-partners/womens-business-centers",
                "category": "nonprofit"
            }
        ]
    
    def create_search_agent(self, name, description, sources):
        """Create a new search agent with specified parameters."""
        if hasattr(self, 'mock_agent_id'):
            return self.mock_agent_id
            
        try:
            payload = {
                "name": name,
                "description": description,
                "sources": sources,
                "capabilities": [
                    "web_search",
                    "website_extraction",
                    "data_transformation"
                ]
            }
            
            response = requests.post(
                f"{self.base_url}/agents",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            
            agent_data = response.json()
            logging.info(f"Created AgentQL search agent: {name}")
            return agent_data.get("agent_id")
            
        except Exception as e:
            logging.error(f"Error creating AgentQL search agent: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logging.error(f"Response: {e.response.text}")
            return None
    
    def search_grants(self, agent_id, query, parameters=None):
        """Execute a grant search using the specified AgentQL agent."""
        if hasattr(self, 'mock_grants'):
            # Filter mock grants based on simple keyword matching
            results = []
            query_lower = query.lower()
            for grant in self.mock_grants:
                # Simple relevance check - include if query terms appear in title or description
                if query_lower in grant['title'].lower() or query_lower in grant['description'].lower():
                    results.append(grant)
            return results
            
        try:
            payload = {
                "agent_id": agent_id,
                "query": query,
                "parameters": parameters or {},
                "response_format": "json",
                "max_tokens": 2000
            }
            
            # Start search
            response = requests.post(
                f"{self.base_url}/search",
                headers=self.headers,
                json=payload
            )
            response.raise_for_status()
            
            search_data = response.json()
            search_id = search_data.get("search_id")
            
            if not search_id:
                logging.error("No search ID returned from AgentQL")
                return []
            
            # Poll for search results
            max_retries = 30
            for i in range(max_retries):
                status_response = requests.get(
                    f"{self.base_url}/search/{search_id}",
                    headers=self.headers
                )
                status_response.raise_for_status()
                
                status_data = status_response.json()
                status = status_data.get("status")
                
                if status == "completed":
                    results = status_data.get("results", [])
                    logging.info(f"AgentQL search completed with {len(results)} results")
                    return self._process_search_results(results)
                
                elif status == "failed":
                    error = status_data.get("error", "Unknown error")
                    logging.error(f"AgentQL search failed: {error}")
                    return []
                
                elif i == max_retries - 1:
                    logging.warning(f"AgentQL search timed out after {max_retries} retries")
                    return []
                
                else:
                    # Wait before polling again (with exponential backoff)
                    wait_time = min(2 ** i, 30)
                    logging.debug(f"Waiting {wait_time}s for AgentQL search to complete...")
                    time.sleep(wait_time)
            
            return []
            
        except Exception as e:
            logging.error(f"Error executing AgentQL search: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logging.error(f"Response: {e.response.text}")
            return []
    
    def _process_search_results(self, results):
        """Process raw search results into structured grant data."""
        grants = []
        
        try:
            for result in results:
                # Extract grant information from search result
                grant_data = {}
                
                # Basic grant information
                grant_data["title"] = result.get("title", "Unknown Grant")
                grant_data["description"] = result.get("content", "No description available")
                grant_data["source_url"] = result.get("url", "")
                grant_data["source"] = self._extract_source_name(result.get("url", ""))
                
                # Additional metadata if available
                metadata = result.get("metadata", {})
                
                if "deadline" in metadata:
                    grant_data["deadline"] = metadata["deadline"]
                
                if "funding_amount" in metadata:
                    grant_data["amount"] = metadata["funding_amount"]
                
                if "eligibility" in metadata:
                    grant_data["eligibility"] = metadata["eligibility"]
                
                grants.append(grant_data)
        
        except Exception as e:
            logging.error(f"Error processing AgentQL search results: {str(e)}")
        
        return grants
    
    def _extract_source_name(self, url):
        """Extract source name from URL."""
        try:
            from urllib.parse import urlparse
            
            if not url:
                return "Unknown Source"
            
            domain = urlparse(url).netloc
            
            # Remove www. prefix if present
            domain = domain.replace("www.", "")
            
            # Extract organization name
            parts = domain.split('.')
            if len(parts) >= 2:
                return parts[0].capitalize()
            else:
                return domain.capitalize()
                
        except Exception:
            return "Unknown Source"
