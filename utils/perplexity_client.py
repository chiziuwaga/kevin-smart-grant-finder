import os
import logging
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional
from utils.clean_extraction import extract_grant_data_clean, extract_grants_with_basic_regex
import asyncio
import httpx

load_dotenv()

# Configure logger for this module
logger = logging.getLogger(__name__)

class PerplexityClient:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Perplexity API client with live API calls only."""
        # Ensure API key is loaded from environment or passed
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("Perplexity API key not found. Please set PERPLEXITY_API_KEY environment variable.")

        self.base_url = "https://api.perplexity.ai"
        self.retry_attempts = 3
        self.default_model = "sonar-reasoning-pro"  # Default to the reasoning model
        self.timeout = 45.0
        
        # Rate limiting settings
        self.rate_limit = int(os.getenv("PERPLEXITY_RATE_LIMIT", 30))
        self._last_request_time = {}
        self._model_delays = {
            "sonar-reasoning-pro": self._calculate_delay_from_rpm(30),
            "sonar-pro": self._calculate_delay_from_rpm(30),
            "llama-3-sonar-large-32k-online": self._calculate_delay_from_rpm(30),
        }
        
        logger.info(f"PerplexityClient initialized with API key: {self.api_key[:10]}... and default model: {self.default_model}")

    def _calculate_delay_from_rpm(self, rpm: int) -> float:
        """Calculate delay between requests based on requests per minute."""
        return 60.0 / rpm if rpm > 0 else 2.0

    async def _apply_rate_limiting(self, model: str):
        """Apply rate limiting based on model."""
        delay = self._model_delays.get(model, 2.0)
        last_time = self._last_request_time.get(model, 0)
        time_since_last = time.monotonic() - last_time
        
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s for model {model}")
            await asyncio.sleep(sleep_time)
        
        self._last_request_time[model] = time.monotonic()

    async def search(self, query: str, model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Execute a search query using Perplexity API with reasoning model."""
        model = model or self.default_model
        
        # Apply rate limiting
        await self._apply_rate_limiting(model)
        
        return await self._execute_search(query, model, **kwargs)

    async def extract_grant_data(self, raw_perplexity_content: Optional[str]) -> List[Dict[str, Any]]:
        """Extract grant data from Perplexity search results using OpenAI GPT-4.1."""
        if not raw_perplexity_content:
            logger.info("No content from Perplexity to extract grants from.")
            return []
            
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.error("OpenAI API key not found. Cannot perform structured extraction. Falling back to basic regex.")
            return extract_grants_with_basic_regex(raw_perplexity_content)
        
        return await extract_grant_data_clean(raw_perplexity_content, openai_api_key)

    async def _execute_search(self, query: str, model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Execute the actual search with Perplexity API."""
        model = model or self.default_model
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a grant research specialist. Search comprehensively for grants using "
                        "reasoning and critical thinking. Provide detailed, structured results with URLs, "
                        "deadlines, eligibility, and funding amounts. Be thorough and creative in your search approach."
                    )
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "temperature": 0.9,  # Creative reasoning
            "max_tokens": 4000,
            **kwargs
        }
        
        logger.debug(f"Executing Perplexity search with model {model}")
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.retry_attempts):
                try:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload
                    )
                    response.raise_for_status()
                    
                    result = response.json()
                    logger.info(f"Perplexity search successful on attempt {attempt + 1}")
                    return result
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        wait_time = 2 ** attempt
                        logger.warning(f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
                        raise
                except httpx.RequestError as e:
                    logger.error(f"Request error on attempt {attempt + 1}: {e}")
                    if attempt == self.retry_attempts - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)
                except Exception as e:
                    logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                    if attempt == self.retry_attempts - 1:
                        raise
                    await asyncio.sleep(2 ** attempt)
        
        raise Exception(f"Failed to complete search after {self.retry_attempts} attempts")

    def get_rate_limit_status(self) -> int:
        """Get current rate limit setting."""
        return self.rate_limit

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model configuration."""
        return {
            "default_model": self.default_model,
            "available_models": list(self._model_delays.keys()),
            "rate_limit": self.rate_limit,
            "timeout": self.timeout
        }
