import os
# import requests # Replaced by httpx for async
import logging
import json
import re
import time
from datetime import datetime # Already present, good
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional # Added typing imports
import httpx # Added for async HTTP requests
import asyncio # For async sleep in mock/retries if needed

load_dotenv()

# Configure logger for this module
logger = logging.getLogger(__name__)
# Basic logging configuration (can be more sophisticated in a central logging_config.py)
# logging.basicConfig(level=logging.INFO) 
# Ensure logging is configured in your main application entry point or logging_config.py

class PerplexityClient:
    def __init__(self, use_mock: bool = False, api_key: Optional[str] = None):
        """Initialize Perplexity API client."""
        self.use_mock = use_mock
        if self.use_mock:
            self._setup_mock_data()
            logger.info("Using mock Perplexity for development")
            return
        # Ensure API key is loaded from environment or passed
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            logger.warning("Perplexity API key not found. Falling back to mock data. Please set PERPLEXITY_API_KEY.")
            self.use_mock = True # Force mock if no key
            self._setup_mock_data()
            return
        self.base_url = "https://api.perplexity.ai"
        self.retry_attempts = 3
        self.models = {
            "sonar-pro": {"rpm": 50, "features": ["images", "search_domain_filter"]},
            "sonar-reasoning-pro": {"rpm": 50, "features": ["images", "search_domain_filter"]},
            "sonar-deep-research": {"rpm": 5, "features": ["related_questions", "structured_outputs"]}
        }
        self.default_model = "sonar-pro" # Default to sonar-pro for speed
        logger.info(f"Perplexity client initialized with models: {list(self.models.keys())}")

    def _setup_mock_data(self):
        """Set up mock data for development."""
        self.mock_results = {
            "choices": [
                {
                    "message": {
                        "content": """Mock Perplexity Response:\nTitle: Mock Grant Alpha\nDescription: A mock grant for testing.\nFunding Amount: $10,000\nDeadline: 2025-12-31\nURL: http://example.com/mockalpha\nEligibility: Mock eligibility criteria.\n\nTitle: Mock Grant Beta\nDescription: Another mock grant for women-owned nonprofits.\nFunding Amount: $25,000\nDeadline: 2026-03-15\nURL: http://example.com/mockbeta\nEligibility: Must be a women-owned nonprofit."""
                    }
                }
            ]
        }
        self.mock_extracted_grants = [
            {
                "title": "Mock Grant Alpha",
                "description": "A mock grant for testing.",
                "deadline": "2025-12-31",
                "funding_amount": "$10,000",
                "eligibility_criteria": "Mock eligibility criteria.",
                "source_url": "http://example.com/mockalpha",
                "source_name": "MockSource"
            }
        ]

    async def search(self, query: str, model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute a search with rate limiting based on model.
        
        Args:
            query: The search query
            model: The model to use (sonar-reasoning-pro or sonar-deep-research)
            **kwargs: Additional parameters like search_domain_filter
        """
        model = model or self.default_model
        if model not in self.models:
            logger.warning(f"Unknown model {model}, falling back to {self.default_model}")
            model = self.default_model
            
        # Rate limiting based on model RPM
        rpm = self.models[model]["rpm"]
        min_interval = 60.0 / rpm  # Minimum seconds between requests
        
        now = time.time()
        if hasattr(self, '_last_request_time'):
            time_since_last = now - self._last_request_time
            if time_since_last < min_interval:
                wait_time = min_interval - time_since_last
                logger.info(f"Rate limiting: waiting {wait_time:.2f}s for {model}")
                await asyncio.sleep(wait_time)
        
        self._last_request_time = time.time()
        
        if self.use_mock:
            # await asyncio.sleep(0.01) 
            if hasattr(self, 'mock_results') and self.mock_results.get("choices"): 
                return self.mock_results["choices"][0]["message"]["content"]
            return "Mock Perplexity response: No specific grants found for this mock query."
            
        current_model = model or self.default_model
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        payload = {
            "model": current_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a specialized grant search assistant. Your task is to find detailed "
                        "information about grant opportunities based on the user query. Focus on extracting and presenting "
                        "key details like title, description, funding amount, deadline, eligibility, and source URL."
                    )
                },
                {
                    "role": "user",
                    "content": query
                }
            ]
        }

        search_domains = kwargs.get('search_domain_filter')
        if search_domains and current_model != "sonar-deep-research":
            payload["search_domain_filter"] = search_domains
            logger.info(f"Using search_domain_filter: {search_domains} with model {current_model}")
        elif search_domains and current_model == "sonar-deep-research":
            logger.warning(f"Model {current_model} does not support search_domain_filter. Domains will be ignored by API. Consider embedding in query text.")
        
        async with httpx.AsyncClient() as client:
            for attempt in range(self.retry_attempts):
                try:
                    logger.debug(f"Attempt {attempt+1} to call Perplexity API. Payload: {json.dumps(payload, indent=2)}")
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=60.0 
                    )
                    response.raise_for_status()
                    response_data = response.json()
                    logger.info(f"Perplexity search successful (model: {current_model}). Query: {query[:100]}...")
                    
                    if response_data.get("choices") and response_data["choices"][0].get("message"): 
                        return response_data["choices"][0]["message"].get("content")
                    else:
                        logger.warning(f"Perplexity response missing expected content structure: {response_data}")
                        return None
                except httpx.HTTPStatusError as e:
                    logger.error(f"HTTP error calling Perplexity API (attempt {attempt+1}/{self.retry_attempts}): {e.response.status_code} - {e.response.text}")
                    if attempt == self.retry_attempts - 1: return None
                    await asyncio.sleep(2 ** attempt)
                except httpx.RequestError as e:
                    logger.error(f"Request error calling Perplexity API (attempt {attempt+1}/{self.retry_attempts}): {e}")
                    if attempt == self.retry_attempts - 1: return None
                    await asyncio.sleep(2 ** attempt)
                except Exception as e:
                    logger.error(f"Unexpected error in Perplexity search (attempt {attempt+1}/{self.retry_attempts}): {e}", exc_info=True)
                    if attempt == self.retry_attempts - 1: return None
                    await asyncio.sleep(2 ** attempt)
        return None

    async def extract_grant_data(self, raw_perplexity_content: Optional[str]) -> List[Dict[str, Any]]:
        """Extract structured grant data from Perplexity search results using OpenAI."""
        if self.use_mock and hasattr(self, 'mock_extracted_grants'):
            # await asyncio.sleep(0.01)
            return self.mock_extracted_grants
        
        if not raw_perplexity_content:
            logger.info("No content from Perplexity to extract grants from.")
            return []
            
        grants = []
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.error("OpenAI API key not found. Cannot perform structured extraction. Falling back to basic regex.")
            return self._extract_grants_with_basic_regex(raw_perplexity_content)

        extraction_payload = {
            "model": "gpt-4o", 
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a grant data extraction assistant. Extract all grant opportunities from the "
                        "provided text. For each grant, include: title (string), description (string), "
                        "deadline (string, YYYY-MM-DD if possible, otherwise as found), "
                        "funding_amount (string, e.g., \"$10,000\" or \"Up to $50,000\"), "
                        "eligibility_criteria (string), source_url (string, a valid URL), and source_name (string, e.g., \"Grants.gov\"). "
                        "Format the response as a JSON object containing a single key \"grants\" which is a list of grant objects. "
                        "If a field is not available, omit it or use null. If no grants are found, return {\"grants\": []}."
                    )
                },
                {
                    "role": "user",
                    "content": f"Extract grant data from the following text:\n\n{raw_perplexity_content}"
                }
            ],
            "response_format": {"type": "json_object"}
        }
        
        headers = {
            "Authorization": f"Bearer {openai_api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=extraction_payload,
                    timeout=45.0
                )
                response.raise_for_status()
                extraction_result = response.json()
                
                if extraction_result.get("choices") and extraction_result["choices"][0].get("message"): 
                    extracted_content_str = extraction_result["choices"][0]["message"].get("content")
                    if extracted_content_str:
                        try:
                            parsed_json = json.loads(extracted_content_str)
                            if isinstance(parsed_json, dict) and "grants" in parsed_json and isinstance(parsed_json["grants"], list):
                                grants = parsed_json["grants"]
                                logger.info(f"Successfully extracted {len(grants)} grants using OpenAI.")
                            else:
                                logger.warning(f"OpenAI extraction returned JSON but not in expected {{'grants': [...]}} format: {parsed_json}")
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to decode JSON from OpenAI extraction: {e}. Content snippet: {extracted_content_str[:500]}")
                    else:
                        logger.info("OpenAI extraction returned no content string.")
                else:
                    logger.warning(f"OpenAI extraction response missing expected structure: {extraction_result}")

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error calling OpenAI API for extraction: {e.response.status_code} - {e.response.text}")
            except httpx.RequestError as e:
                logger.error(f"Request error calling OpenAI API for extraction: {e}")
            except Exception as e:
                logger.error(f"Unexpected error during OpenAI grant data extraction: {e}", exc_info=True)
        
        if not grants: 
            logger.info("OpenAI extraction yielded no grants or failed, attempting basic regex fallback.")
            grants = self._extract_grants_with_basic_regex(raw_perplexity_content)

        return grants

    def _extract_grants_with_basic_regex(self, content: Optional[str]) -> List[Dict[str, Any]]:
        """A very basic regex-based fallback for grant extraction if LLM fails or content is None."""
        if not content:
            return []
        logger.warning("Using basic regex fallback for grant extraction. Results may be limited/inaccurate.")
        grants = []
        try:
            grant_blocks = re.split(r'\n\s*(?:\d+\.|\*|-)\s+|\n---\n', content) 
            if len(grant_blocks) <=1 : grant_blocks = content.split("\n\n") 

            for block_text in grant_blocks:
                if len(block_text.strip()) < 75: 
                    continue

                title_match = re.search(r"^(?:Title|Grant Name|Opportunity):\s*(.+?)(?:\n|$)", block_text, re.IGNORECASE | re.MULTILINE)
                if not title_match:
                    first_line = block_text.strip().split('\n')[0]
                    if len(first_line) < 150 and len(first_line) > 5 : 
                        title = first_line
                    else:
                        continue 
                else:
                    title = title_match.group(1).strip()

                description = block_text 
                desc_match = re.search(r"Description:\s*(.+?)(?:\n\s*(?:Deadline|Amount|Eligibility|URL)|$)", block_text, re.IGNORECASE | re.DOTALL)
                if desc_match: description = desc_match.group(1).strip()
                
                deadline_match = re.search(r"Deadline(?:s)?:\s*([^\n]+)", block_text, re.IGNORECASE)
                amount_match = re.search(r"(?:Funding Amount|Amount):\s*([^\n]+)", block_text, re.IGNORECASE)
                url_match = re.search(r"(?:URL|Link|Website|Source URL):\s*(https?://[^\s]+)", block_text, re.IGNORECASE)
                eligibility_match = re.search(r"Eligibility(?: Criteria)?:\s*([^\n]+)(?:\n|$)", block_text, re.IGNORECASE)

                grants.append({
                    "title": title,
                    "description": description,
                    "deadline": deadline_match.group(1).strip() if deadline_match else None,
                    "funding_amount": amount_match.group(1).strip() if amount_match else None,
                    "source_url": url_match.group(1).strip() if url_match else None,
                    "eligibility_criteria": eligibility_match.group(1).strip() if eligibility_match else "See source for details",
                    "source_name": "Perplexity Extraction Fallback"
                })
        except Exception as e:
            logger.error(f"Error during basic regex grant extraction: {e}", exc_info=True)

        if grants:
            logger.info(f"Basic regex fallback extracted {len(grants)} potential grants.")
        return grants

    async def _execute_search(self, query: str, model: str = None, **kwargs) -> Dict[str, Any]:
        """Execute search with proper model handling and retries."""
        if self.use_mock:
            return self.mock_results
            
        current_model = model or self.default_model
        search_domain_filter = kwargs.get('search_domain_filter')
        structured_output = kwargs.get('structured_output', False)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": current_model,
            "messages": [{
                "role": "user",
                "content": query
            }]
        }
        
        # Add model-specific parameters
        if current_model == "sonar-reasoning-pro" and search_domain_filter:
            payload["search_domain_filter"] = search_domain_filter
            logger.info(f"Using search_domain_filter: {search_domain_filter} with model {current_model}")
        
        if current_model == "sonar-deep-research" and structured_output:
            # Enhance query for structured output
            payload["messages"][0]["content"] = f"{query}\n\nPlease provide results in a structured format including:\n- Title\n- Description\n- Funding Amount\n- Deadline\n- Eligibility\n- Source URL"
            
        for attempt in range(self.retry_attempts):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        logger.info(f"Perplexity search successful (model: {current_model}). Query: {query[:100]}...")
                        return response.json()
                    else:
                        logger.error(f"HTTP error calling Perplexity API (attempt {attempt + 1}/{self.retry_attempts}): {response.status_code} - {response.text}")
                        
                        if response.status_code == 429:  # Rate limit
                            wait_time = min(2 ** attempt, 8)  # Exponential backoff
                            logger.info(f"Rate limited. Waiting {wait_time}s before retry...")
                            await asyncio.sleep(wait_time)
                            continue
                            
            except Exception as e:
                logger.error(f"Error calling Perplexity API (attempt {attempt + 1}/{self.retry_attempts}): {str(e)}")
                
            if attempt < self.retry_attempts - 1:
                wait_time = min(2 ** attempt, 8)
                await asyncio.sleep(wait_time)
                
        logger.error("All attempts to call Perplexity API failed")
        return {"choices": [{"message": {"content": ""}}]}

    def _parse_grant_data(self, content: str) -> List[Dict[str, Any]]:
        """Parse grant data from API response with robust field extraction."""
        grants = []
        current_grant = {}
        
        # Common patterns for grant fields
        patterns = {
            "title": r"(?i)title:\s*(.+?)(?=\n|$)",
            "description": r"(?i)description:\s*(.+?)(?=\n|$)",
            "funding_amount": r"(?i)funding.?amount:\s*([^\n]+)",
            "deadline": r"(?i)deadline:\s*(.+?)(?=\n|$)",
            "eligibility": r"(?i)eligibility:\s*(.+?)(?=\n|$)",
            "source_url": r"(?i)(?:source.?url|url|link):\s*(\S+)"
        }
        
        # Split content into individual grant blocks
        grant_blocks = re.split(r'\n\s*\n|(?=Title:)', content)
        
        for block in grant_blocks:
            if not block.strip():
                continue
                
            grant_data = {}
            
            # Extract fields using patterns
            for field, pattern in patterns.items():
                match = re.search(pattern, block, re.MULTILINE | re.IGNORECASE)
                if match:
                    grant_data[field] = match.group(1).strip()
            
            # Only include grants that have at least title and one other field
            if grant_data.get('title') and len(grant_data) > 1:
                # Clean and normalize data
                if 'funding_amount' in grant_data:
                    # Extract numeric amount and range
                    amount_str = grant_data['funding_amount']
                    amount_match = re.search(r'[\d,]+', amount_str)
                    if amount_match:
                        grant_data['funding_amount'] = float(amount_match.group().replace(',', ''))
                        
                if 'deadline' in grant_data:
                    # Try to parse and normalize date
                    try:
                        date_str = grant_data['deadline']
                        # Add various date format parsing here
                        parsed_date = datetime.strptime(date_str, '%Y-%m-%d')
                        grant_data['deadline'] = parsed_date.isoformat()
                    except ValueError:
                        # Keep original if parsing fails
                        pass
                
                grants.append(grant_data)
        
        return grants
