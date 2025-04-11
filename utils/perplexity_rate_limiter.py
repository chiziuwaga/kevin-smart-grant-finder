"""
Rate limit handler for Perplexity API to manage quotas and provide fallbacks.
This module helps prevent API failures due to rate limits by implementing
proper retry logic, exponential backoff, and alternative search methods.
"""

import logging
import time
from datetime import datetime, timedelta
import requests
import json
import os
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger(__name__)

class PerplexityRateHandler:
    """
    Manages rate limits for the Perplexity API to ensure reliable operation.
    
    Features:
    - Exponential backoff for transient errors
    - Quota tracking
    - Automatic fallback to alternative search methods
    """
    
    def __init__(self, api_key: str = None):
        """
        Initialize the rate limit handler.
        
        Args:
            api_key: Perplexity API key (optional, will use env var if not provided)
        """
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("Perplexity API key not found")
            
        # Rate limiting state
        self.daily_quota_used = False
        self.daily_quota_reset_time = None
        self.minute_quota_reset_time = None
        self.request_count = 0
        self.max_requests_per_minute = 20  # Default, may be adjusted based on tier
        self.last_minute = datetime.now().minute
        
        # Backoff configuration
        self.base_backoff = 1.0  # Initial backoff in seconds
        self.max_backoff = 60.0  # Maximum backoff in seconds
        self.current_backoff = self.base_backoff
        
        logger.info("Perplexity Rate Handler initialized")
    
    def execute_with_rate_handling(self, search_func: Callable, 
                                  *args, 
                                  fallback_func: Optional[Callable] = None,
                                  max_retries: int = 5,
                                  **kwargs) -> Dict[str, Any]:
        """
        Execute a Perplexity API call with comprehensive rate limit handling.
        
        Args:
            search_func: The function to call (e.g., perplexity_client.deep_search)
            *args: Positional arguments to pass to the search function
            fallback_func: Alternative function to call if Perplexity fails
            max_retries: Maximum number of retry attempts
            **kwargs: Keyword arguments to pass to the search function
            
        Returns:
            The search results or fallback results
        """
        # Reset per-minute counter if we're in a new minute
        current_minute = datetime.now().minute
        if current_minute != self.last_minute:
            self.request_count = 0
            self.last_minute = current_minute
        
        # Check if we've hit daily quota
        if self.daily_quota_used and self.daily_quota_reset_time:
            if datetime.now() < self.daily_quota_reset_time:
                time_until_reset = (self.daily_quota_reset_time - datetime.now()).total_seconds()
                logger.warning(f"Daily quota still exceeded. Try again in {time_until_reset:.1f} seconds or use fallback.")
                return self._use_fallback(fallback_func, *args, **kwargs)
            else:
                # Reset daily quota flag if reset time has passed
                logger.info("Daily quota reset time has passed, resetting quota flag")
                self.daily_quota_used = False
        
        # Check if we've hit per-minute quota
        if self.minute_quota_reset_time and datetime.now() < self.minute_quota_reset_time:
            time_until_reset = (self.minute_quota_reset_time - datetime.now()).total_seconds()
            logger.info(f"Per-minute quota exceeded. Waiting {time_until_reset:.1f}s before next request")
            time.sleep(time_until_reset)
            self.request_count = 0
        
        # Track request count for rate limiting
        self.request_count += 1
        if self.request_count >= self.max_requests_per_minute:
            logger.info(f"Approaching per-minute limit ({self.request_count}/{self.max_requests_per_minute})")
        
        # Attempt the API call with retries
        for attempt in range(max_retries):
            try:
                logger.debug(f"Making Perplexity API call (attempt {attempt+1}/{max_retries})")
                result = search_func(*args, **kwargs)
                
                # Reset backoff on success
                self.current_backoff = self.base_backoff
                return result
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Too Many Requests
                    # Check response headers for rate limit information
                    headers = e.response.headers
                    
                    # Daily quota reset (check for Retry-After or custom header)
                    retry_after = headers.get('Retry-After') or headers.get('X-RateLimit-Reset')
                    
                    if retry_after and int(retry_after) > 300:  # More than 5 minutes
                        # Likely a daily quota reset
                        logger.warning(f"Daily quota exceeded - reset in {retry_after} seconds")
                        self.daily_quota_used = True
                        self.daily_quota_reset_time = datetime.now() + timedelta(seconds=int(retry_after))
                        return self._use_fallback(fallback_func, *args, **kwargs)
                    
                    elif retry_after:
                        # Per-minute rate limit
                        wait_seconds = min(int(retry_after), 60)
                        logger.info(f"Rate limited. Waiting {wait_seconds}s before retry.")
                        self.minute_quota_reset_time = datetime.now() + timedelta(seconds=wait_seconds)
                        time.sleep(wait_seconds)
                        continue
                    
                    else:
                        # No clear reset time, use exponential backoff
                        logger.info(f"Rate limited. Using exponential backoff: {self.current_backoff}s")
                        time.sleep(self.current_backoff)
                        self.current_backoff = min(self.current_backoff * 2, self.max_backoff)
                        continue
                
                elif e.response.status_code >= 500:
                    # Server error - retry with backoff
                    logger.warning(f"Perplexity server error: {e.response.status_code}. Retrying in {self.current_backoff}s")
                    time.sleep(self.current_backoff)
                    self.current_backoff = min(self.current_backoff * 2, self.max_backoff)
                    continue
                
                else:
                    # Other HTTP error
                    logger.error(f"HTTP error accessing Perplexity API: {e}")
                    if attempt == max_retries - 1:
                        return self._use_fallback(fallback_func, *args, **kwargs)
                    time.sleep(self.current_backoff)
                    self.current_backoff = min(self.current_backoff * 2, self.max_backoff)
            
            except requests.exceptions.RequestException as e:
                # Network or timeout error
                logger.error(f"Request error accessing Perplexity API: {e}")
                if attempt == max_retries - 1:
                    return self._use_fallback(fallback_func, *args, **kwargs)
                time.sleep(self.current_backoff)
                self.current_backoff = min(self.current_backoff * 2, self.max_backoff)
            
            except Exception as e:
                # Unexpected error
                logger.error(f"Unexpected error during Perplexity API call: {e}", exc_info=True)
                if attempt == max_retries - 1:
                    return self._use_fallback(fallback_func, *args, **kwargs)
                time.sleep(self.current_backoff)
                self.current_backoff = min(self.current_backoff * 2, self.max_backoff)
        
        # If we've exhausted retries
        logger.warning(f"Exhausted {max_retries} retries for Perplexity API call")
        return self._use_fallback(fallback_func, *args, **kwargs)
    
    def _use_fallback(self, fallback_func, *args, **kwargs):
        """Use alternative search method when Perplexity is unavailable."""
        if fallback_func:
            logger.info("Using fallback search method instead of Perplexity")
            try:
                return fallback_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in fallback function: {e}")
                return self._empty_result()
        else:
            logger.warning("No fallback function provided, returning empty result")
            return self._empty_result()
    
    def _empty_result(self):
        """Return an empty result structure compatible with Perplexity API."""
        return {
            "choices": [],
            "id": "fallback_empty_result",
            "model": "none",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        }

    def update_quota_limits(self, tier):
        """Update rate limits based on API tier."""
        if tier == "free":
            self.max_requests_per_minute = 5
        elif tier == "pro":
            self.max_requests_per_minute = 20
        elif tier == "enterprise":
            self.max_requests_per_minute = 60
        else:
            self.max_requests_per_minute = 5  # Default to most conservative limit
            
        logger.info(f"Updated rate limits to {self.max_requests_per_minute} requests per minute ({tier} tier)")


class AgentQLFallbackSearcher:
    """Provides alternative search capabilities when Perplexity is unavailable."""
    
    def __init__(self, agentql_client):
        """Initialize with an AgentQL client."""
        self.agentql_client = agentql_client
        self.telecom_agent_id = None
        self.nonprofit_agent_id = None
        
        logger.info("AgentQL fallback searcher initialized")
    
    def search(self, query, site_restrictions=None, max_results=20, category=None):
        """
        Perform a search using AgentQL as a fallback for Perplexity.
        
        Args:
            query: The search query
            site_restrictions: List of site restrictions (ignored, handled by agent setup)
            max_results: Maximum number of results to return
            category: Optional category to determine which agent to use
            
        Returns:
            Dict with a structure similar to Perplexity API response
        """
        try:
            # Ensure we have appropriate agents
            self._ensure_agents()
            
            # Determine which agent to use
            agent_id = self._get_agent_for_category(category)
            if not agent_id:
                logger.warning("No suitable agent found for fallback search")
                return self._empty_result()
            
            # Execute search via AgentQL
            logger.info(f"Executing fallback search with AgentQL agent {agent_id}")
            results = self.agentql_client.search_grants(
                agent_id=agent_id,
                query=query,
                parameters={"max_results": max_results}
            )
            
            # Convert to Perplexity-like structure
            if results:
                response_text = self._format_results_as_text(results)
                return {
                    "choices": [{
                        "message": {
                            "content": response_text,
                            "role": "assistant"
                        }
                    }],
                    "id": f"agentql_fallback_{agent_id}",
                    "model": "agentql_fallback",
                    "usage": {"total_tokens": len(response_text) // 4}  # Rough estimate
                }
            else:
                return self._empty_result()
                
        except Exception as e:
            logger.error(f"Error in AgentQL fallback search: {e}", exc_info=True)
            return self._empty_result()
    
    def _ensure_agents(self):
        """Ensure that search agents are created if needed."""
        try:
            if not self.telecom_agent_id:
                self.telecom_agent_id = self.agentql_client.create_search_agent(
                    name="TelecomGrantFinder",
                    description="Searches for telecommunications grant opportunities",
                    sources=["grants.gov", "rd.usda.gov", "fcc.gov", "ntia.gov"]
                )
                
            if not self.nonprofit_agent_id:
                self.nonprofit_agent_id = self.agentql_client.create_search_agent(
                    name="NonprofitGrantFinder",
                    description="Searches for grants for women-owned nonprofits",
                    sources=["grants.gov", "sba.gov", "ifundwomen.com"]
                )
        except Exception as e:
            logger.error(f"Error creating AgentQL agents: {e}")
    
    def _get_agent_for_category(self, category):
        """Get the appropriate agent ID based on the category."""
        if not category or category == "unknown":
            # Default to telecom if no category specified
            return self.telecom_agent_id or self.nonprofit_agent_id
            
        elif category.lower() in ["telecom", "telecommunications", "broadband"]:
            return self.telecom_agent_id
            
        elif category.lower() in ["nonprofit", "women-owned", "women"]:
            return self.nonprofit_agent_id
            
        else:
            # Default to telecom for other categories
            return self.telecom_agent_id
    
    def _format_results_as_text(self, results):
        """Format search results as structured text similar to Perplexity output."""
        formatted_text = "Here are the grant opportunities I found:\n\n"
        
        for i, grant in enumerate(results, 1):
            formatted_text += f"{i}. **{grant.get('title', 'Grant Opportunity')}**\n"
            formatted_text += f"   Description: {grant.get('description', 'No description available')[:200]}...\n"
            if 'deadline' in grant:
                formatted_text += f"   Deadline: {grant['deadline']}\n"
            if 'amount' in grant:
                formatted_text += f"   Amount: {grant['amount']}\n"
            if 'eligibility' in grant:
                formatted_text += f"   Eligibility: {grant['eligibility'][:100]}...\n"
            formatted_text += f"   Source: {grant.get('source_name', 'Unknown')}\n"
            formatted_text += f"   URL: {grant.get('source_url', '#')}\n\n"
        
        if not results:
            formatted_text += "No results found matching your criteria."
            
        return formatted_text
    
    def _empty_result(self):
        """Return an empty result structure."""
        return {
            "choices": [{
                "message": {
                    "content": "No results found matching your criteria.",
                    "role": "assistant"
                }
            }],
            "id": "agentql_fallback_empty",
            "model": "agentql_fallback",
            "usage": {"total_tokens": 0}
        } 