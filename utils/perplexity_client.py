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
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Perplexity API client with live API calls only."""        # Ensure API key is loaded from environment or passed
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("Perplexity API key not found. Please set PERPLEXITY_API_KEY environment variable.")

        self.base_url = "https://api.perplexity.ai"
        self.retry_attempts = 3
        self._last_request_time = 0
        
        # Updated models configuration with clear capabilities
        self.models = {
            "sonar-pro": {
                "rpm": 50,  # Requests per minute
                "features": ["search_domain_filter", "structured_output"],
                "timeout": 60.0,  # Default timeout in seconds
                "is_default": True
            },
            "sonar-medium-online": {
                "rpm": 100,
                "features": ["search_domain_filter"],
                "timeout": 30.0
            },
            "sonar-small-online": {
                "rpm": 200,
                "features": ["search_domain_filter"],
                "timeout": 15.0
            }
        }
        
        self.default_model = "sonar-pro"  # Best for complex tasks like grant analysis
        self._rate_limiters = {
            model: self._create_rate_limiter(config["rpm"])
            for model, config in self.models.items()
        }
        
        logger.info(f"Perplexity client initialized with default model: {self.default_model}")

    async def search(self, query: str, model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Execute a search query against the Perplexity API with rate limiting and retries.
        
        Args:
            query: The search query text
            model: Optional model override (defaults to self.default_model)
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            Dict containing the API response
        """
        return await self._execute_search(query, model=model, **kwargs)

    async def extract_grant_data(self, raw_perplexity_content: Optional[str]) -> List[Dict[str, Any]]:
        """Extract structured grant data from Perplexity search results using OpenAI (o1-mini)."""
        if not raw_perplexity_content:
            logger.info("No content from Perplexity to extract grants from.")
            return []
            
        grants = []
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.error("OpenAI API key not found. Cannot perform structured extraction. Falling back to basic regex.")
            return self._extract_grants_with_basic_regex(raw_perplexity_content)

        extraction_payload = {
            "model": "o1-mini", 
            "messages": [
                {
                    "role": "system",                    "content": (
                        "You are a grant data extraction assistant. Extract all grant opportunities from the "
                        "provided text. For each grant, format the data as follows:\n\n"
                        "- title (string): Required. Clear, concise title without trailing periods.\n"
                        "- description (string): Required. Detailed description of the grant purpose and requirements.\n"
                        "- deadline (string): Format as YYYY-MM-DD. If not exact date, use the latest possible date mentioned.\n"
                        "- funding_amount (number): Convert to numeric value, use maximum for ranges. Omit currency symbols.\n"
                        "- eligibility_criteria (string): Who can apply, requirements, and restrictions.\n"
                        "- category (string): Grant type (e.g., 'research', 'education', 'nonprofit').\n"
                        "- source_url (string): Must be a valid, complete URL starting with http(s)://.\n"
                        "- source_name (string): Name of the granting organization or platform.\n"
                        "- score (number, optional): If relevance score available, provide as 0-100 float.\n\n"
                        "Format response as JSON: {\"grants\": [...]}\n"
                        "For missing required fields, use null. Omit optional fields if not found.\n"
                        "Ensure all dates are future dates or null if past.\n"
                        "Ensure funding amounts are positive numbers or null if unclear."
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
                eligibility_match = re.search(r"Eligibility(?: Criteria)?:\s*([^\n]+)(?:\n|$)", block_text, re.IGNORECASE)                # Process funding amount
                funding_amount = None
                if amount_match:
                    amount_str = amount_match.group(1).strip()
                    # Handle ranges and normalize amount
                    range_match = re.search(r'(?:[\$£€]?\s*)([\d,]+(?:\.\d+)?)\s*(?:-|to)\s*([\d,]+(?:\.\d+)?)', amount_str)
                    if range_match:
                        amount1 = float(range_match.group(1).replace(',', ''))
                        amount2 = float(range_match.group(2).replace(',', ''))
                        funding_amount = max(amount1, amount2)
                    else:
                        amount_match = re.search(r'(?:[\$£€]?\s*)([\d,]+(?:\.\d+)?)', amount_str)
                        if amount_match:
                            funding_amount = float(amount_match.group(1).replace(',', ''))

                # Process deadline
                deadline = None
                if deadline_match:
                    try:
                        date_str = deadline_match.group(1).strip()
                        for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%B %d, %Y', '%b %d, %Y']:
                            try:
                                parsed_date = datetime.strptime(date_str, fmt)
                                if parsed_date > datetime.now():
                                    deadline = parsed_date.isoformat()
                                    break
                            except ValueError:
                                continue
                    except Exception as e:
                        logger.warning(f"Error parsing deadline in regex fallback: {e}")

                grants.append({
                    "title": title,
                    "description": description,
                    "deadline": deadline,
                    "funding_amount": funding_amount,
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
                if 'funding_amount' in grant_data:                    # Extract and normalize funding amount
                    amount_str = grant_data['funding_amount']
                    # Handle ranges like "10,000 - 50,000" or "Up to 50,000"
                    range_match = re.search(r'(?:[\$£€]?\s*)([\d,]+(?:\.\d+)?)\s*(?:-|to)\s*([\d,]+(?:\.\d+)?)', amount_str)
                    if range_match:
                        # For ranges, use the maximum amount
                        amount1 = float(range_match.group(1).replace(',', ''))
                        amount2 = float(range_match.group(2).replace(',', ''))
                        grant_data['funding_amount'] = max(amount1, amount2)
                    else:
                        # Handle single amounts
                        amount_match = re.search(r'(?:[\$£€]?\s*)([\d,]+(?:\.\d+)?)', amount_str)
                        if amount_match:
                            grant_data['funding_amount'] = float(amount_match.group(1).replace(',', ''))
                          # Validate amount is positive
                    if grant_data.get('funding_amount', 0) < 0:
                        logger.warning(f"Invalid negative funding amount found: {amount_str}")
                        grant_data['funding_amount'] = None

                if 'deadline' in grant_data:
                    # Try to parse and normalize date with multiple format support
                    try:
                        date_str = grant_data['deadline']
                        # Common date formats to try
                        date_formats = [
                            '%Y-%m-%d',           # 2023-12-31
                            '%m/%d/%Y',           # 12/31/2023
                            '%d/%m/%Y',           # 31/12/2023
                            '%B %d, %Y',          # December 31, 2023
                            '%b %d, %Y',          # Dec 31, 2023
                            '%d %B %Y',           # 31 December 2023
                            '%d %b %Y',           # 31 Dec 2023
                            '%m-%d-%Y',           # 12-31-2023
                            '%Y/%m/%d'            # 2023/12/31
                        ]
                        
                        parsed_date = None
                        for fmt in date_formats:
                            try:
                                parsed_date = datetime.strptime(date_str, fmt)
                                break
                            except ValueError:
                                continue
                        if parsed_date:
                            # Only use future dates
                            if parsed_date > datetime.now():
                                # Use ISO format for consistent API responses
                                grant_data['deadline'] = parsed_date.isoformat()
                            else:
                                logger.warning(f"Skipping past deadline: {date_str}")
                                grant_data['deadline'] = None
                    except Exception as e:
                        logger.warning(f"Error parsing deadline in regex fallback: {e}")
                        grant_data['deadline'] = None
                
                grants.append(grant_data)
        
        return grants

    def _create_rate_limiter(self, rpm: int) -> float:
        """
        Create a rate limiter for a specific model based on its RPM limit.
        
        Args:
            rpm: Requests per minute limit for the model
            
        Returns:
            float: Minimum delay between requests in seconds
        """
        # Convert RPM to minimum delay between requests
        min_delay = 60.0 / float(rpm)  # Ensure float division
        logger.debug(f"Creating rate limiter with {rpm} RPM (min delay: {min_delay:.2f}s)")
        return min_delay

    def get_rate_limit_status(self) -> int:
        """Get current rate limit status.
        
        Returns:
            int: Estimated remaining requests for current minute
        """
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        # Simple estimation: assume we can make requests at the default model's rate
        default_model_config = self.models.get(self.default_model, {})
        rpm = default_model_config.get("rpm", 50)
        
        # Estimate remaining capacity (very simplified)
        if time_since_last < 60:
            return max(0, rpm - 5)  # Conservative estimate
        else:
            return rpm  # Full capacity if it's been more than a minute
