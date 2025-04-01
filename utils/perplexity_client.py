import os
import requests
import logging
import json
import re
import time
from datetime import datetime, timezone # Added timezone
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class PerplexityRateLimitHandler:
    """Handles rate limiting, backoff, and fallback for Perplexity API calls."""
    def __init__(self, client_instance):
        self.client_instance = client_instance # Reference to the PerplexityClient
        self.backoff_time = 1  # Start with 1 second
        self.max_backoff = 60  # Maximum backoff of 60 seconds
        self.retry_count = 0
        self.max_retries = 5
        # daily_quota_reset_time removed, logic relies on wait_seconds calculation

    def execute_with_rate_limit_handling(self, search_function, *args, **kwargs):
        """Execute a Perplexity API call with rate limit handling."""
        self.retry_count = 0 # Reset retry count for each new high-level call
        while self.retry_count < self.max_retries:
            try:
                result = search_function(*args, **kwargs)

                # Reset backoff on success
                self.backoff_time = 1
                logger.debug(f"Perplexity API call successful.")
                return result

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Too Many Requests
                    logger.warning(f"Perplexity API rate limit hit (Status 429). Retry {self.retry_count + 1}/{self.max_retries}.")
                    # Check for reset header (value is Unix timestamp)
                    reset_header = e.response.headers.get("X-RateLimit-Reset")
                    wait_seconds = self.backoff_time # Default wait is current backoff

                    if reset_header:
                        try:
                            reset_timestamp = int(reset_header)
                            reset_time = datetime.fromtimestamp(reset_timestamp, tz=timezone.utc)
                            now_utc = datetime.now(timezone.utc)
                            # Calculate wait time based on header, minimum 1 second
                            header_wait_seconds = max(1, (reset_time - now_utc).total_seconds())

                            if header_wait_seconds > 300:  # More than 5 minutes - likely daily quota
                                logger.error(f"Perplexity quota likely exceeded. Reset time: {reset_time}. Aborting Perplexity search.")
                                # Cannot fallback here directly, raise specific exception
                                raise PerplexityQuotaExceededError(f"Daily quota likely hit. Reset at {reset_time}")
                            else:
                                # Use the longer of the header wait time or current backoff
                                wait_seconds = max(header_wait_seconds, self.backoff_time)
                                logger.info(f"Rate limit reset specified at {reset_time}. Waiting {wait_seconds:.1f} seconds.")

                        except (ValueError, TypeError):
                            logger.warning("Could not parse X-RateLimit-Reset header. Using default backoff.")
                            wait_seconds = self.backoff_time
                    else:
                         logger.info(f"No X-RateLimit-Reset header found. Using default backoff: {self.backoff_time}s.")
                         wait_seconds = self.backoff_time

                    # Apply wait time, capped by max backoff
                    actual_wait = min(wait_seconds, self.max_backoff)
                    logger.info(f"Waiting {actual_wait:.1f}s before retrying Perplexity call.")
                    time.sleep(actual_wait)

                    # Increase backoff time for next potential failure, capped
                    self.backoff_time = min(self.backoff_time * 2, self.max_backoff)
                    self.retry_count += 1
                    continue # Retry the loop

                else:
                    # Other HTTP errors - log and re-raise or handle as fatal
                    logger.error(f"HTTP error {e.response.status_code} in Perplexity API call: {e.response.text}")
                    raise # Re-raise for the outer layer to potentially handle or fail

            except requests.exceptions.RequestException as req_e:
                logger.error(f"RequestException during Perplexity call: {str(req_e)}")
                # Decide if retryable or raise
                if self.retry_count < self.max_retries:
                    wait_time = min(self.backoff_time, self.max_backoff)
                    logger.warning(f"Connection error. Waiting {wait_time}s before retry {self.retry_count + 1}/{self.max_retries}.")
                    time.sleep(wait_time)
                    self.backoff_time = min(self.backoff_time * 2, self.max_backoff)
                    self.retry_count += 1
                    continue
                else:
                    logger.error("Max retries exceeded for connection errors.")
                    raise PerplexityConnectionError("Failed to connect to Perplexity after multiple retries.") from req_e

            except Exception as e:
                logger.error(f"Unexpected error during Perplexity API call: {str(e)}", exc_info=True)
                # Unexpected errors usually shouldn't be retried, re-raise
                raise # Re-raise the unexpected error

        # If loop finishes (max retries exceeded)
        logger.error(f"Exceeded maximum retries ({self.max_retries}) for Perplexity API call due to rate limits.")
        raise PerplexityRateLimitError(f"Max retries ({self.max_retries}) exceeded for Perplexity.")

# Custom Exceptions for Perplexity Errors
class PerplexityError(Exception):
    """Base exception for Perplexity client errors."""
    pass

class PerplexityRateLimitError(PerplexityError):
    """Raised when max retries are hit due to rate limits."""
    pass

class PerplexityQuotaExceededError(PerplexityError):
    """Raised when the daily quota is likely exceeded."""
    pass

class PerplexityConnectionError(PerplexityError):
     """Raised when connection fails after retries."""
     pass

class PerplexityClient:
    def __init__(self):
        """Initialize Perplexity API client for deep research."""
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            logger.error("Perplexity API key not found in environment variables. Perplexity searches will fail.")
            self.base_url = None
            # Don't instantiate handler if API key is missing
            self.rate_limit_handler = None
            return
            # raise ValueError("Perplexity API key not found in environment variables")

        self.base_url = "https://api.perplexity.ai"
        self.rate_limit_handler = PerplexityRateLimitHandler(self)
        logger.info("Perplexity client initialized")

    def is_available(self):
        """Check if the client was initialized correctly."""
        return bool(self.api_key and self.base_url)

    def _perform_search_request(self, query, site_restrictions=None):
        """Internal method to make the actual API request."""
        if not self.is_available():
            raise PerplexityError("Perplexity client is not available (missing API key).")

        # Build complete search query with site restrictions
        complete_query = query
        if site_restrictions:
            site_query = " OR ".join([f"site:{site}" for site in site_restrictions]) # Fix: added site: prefix
            complete_query = f"{query} ({site_query})"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            # "model": "sonar-medium-online", # Use a potentially cheaper/faster model if needed
            "model": "llama-3-sonar-large-32k-online", # Updated model
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a specialized grant search assistant. Your task is to find detailed "
                        "information about grant opportunities, including deadlines, amounts, eligibility "
                        "requirements, source URLs, and application processes. Focus on extracting specific facts."
                    )
                },
                {
                    "role": "user",
                    "content": complete_query
                }
            ]
        }

        logger.debug(f"Sending Perplexity search request. Query length: {len(complete_query)}")
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=60  # 60-second timeout
        )
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        return response.json()

    def deep_search(self, query, site_restrictions=None, max_results=100):
        """Perform a deep search using Perplexity API with rate limit handling."""
        if not self.rate_limit_handler:
             logger.error("Perplexity client not initialized correctly. Cannot perform search.")
             return {"error": "Perplexity client not initialized"}
        try:
            # Use the handler to execute the request
            result = self.rate_limit_handler.execute_with_rate_limit_handling(
                self._perform_search_request,
                query,
                site_restrictions=site_restrictions
                # max_results is not directly supported by Perplexity API, filtering happens post-search
            )
            logger.info(f"Perplexity deep search completed successfully for query fragment: {query[:50]}...")
            return result
        except (PerplexityRateLimitError, PerplexityQuotaExceededError, PerplexityConnectionError, PerplexityError) as e:
             logger.error(f"Perplexity search failed: {str(e)}")
             # Return an error structure consistent with successful calls but indicating failure
             return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error during Perplexity deep search orchestration: {str(e)}", exc_info=True)
            return {"error": f"Unexpected error: {str(e)}"}

    def extract_grant_data(self, search_results):
        """Extract structured grant data from Perplexity search results."""
        grants = []
        if not search_results or "error" in search_results:
             logger.warning(f"Cannot extract grants, search results indicate an error: {search_results.get('error')}")
             return grants

        try:
            if "choices" in search_results and search_results["choices"]:
                content = search_results["choices"][0]["message"]["content"]
                logger.debug(f"Raw content from Perplexity for extraction: {content[:500]}...")

                # --- Fallback to Regex Extraction --- 
                # The structured extraction via OpenAI/GPT-4o adds cost and complexity.
                # Let's rely on robust regex first, which is often sufficient for this task.
                grants = self._extract_grants_with_regex(content)
                if grants:
                    logger.info(f"Successfully extracted {len(grants)} grants from Perplexity results using regex.")
                else:
                    logger.warning("Regex extraction yielded no grants from Perplexity content.")
                # --- End Regex Fallback --- 

            else:
                logger.warning("No 'choices' found in Perplexity search results.")

        except Exception as e:
            logger.error(f"Error processing Perplexity search results for extraction: {str(e)}", exc_info=True)

        # Basic validation step (ensure title, description, and URL exist)
        validated_grants = []
        for grant in grants:
            if grant.get("title") and grant.get("description") and grant.get("source_url"):
                 # Simple date parsing attempt (can be enhanced)
                 if isinstance(grant.get("deadline"), str):
                     grant["deadline"] = self._parse_deadline_flexible(grant["deadline"])
                 validated_grants.append(grant)
            else:
                 logger.debug(f"Skipping grant due to missing core fields: Title={grant.get('title')}, URL={grant.get('source_url')}")

        logger.info(f"Returning {len(validated_grants)} validated grants after extraction.")
        return validated_grants

    def _extract_grants_with_regex(self, text):
        """Extract grant information using regex patterns."""
        grants = []
        # Regex to find potential grant blocks, looking for common headers
        # Split based on lines that look like headers (e.g., bold text, Title:, Grant Name:, ##)
        # This is a simple approach; more complex HTML parsing might be better if source allows
        potential_blocks = re.split(r'\n(?:\*\*|##|\d+\.|\* |- )\s*([A-Z][A-Za-z\s]+:?)\s*\n', text)

        # Add the initial text block if the split occurs mid-text
        processed_text = potential_blocks[0]
        grant_blocks = []
        # Reconstruct blocks based on potential headers
        if len(potential_blocks) > 1:
             for i in range(1, len(potential_blocks), 2):
                 header = potential_blocks[i]
                 content = potential_blocks[i+1] if (i+1) < len(potential_blocks) else ""
                 grant_blocks.append(f"\n{header}\n{content}")
        else:
             grant_blocks.append(processed_text) # Treat the whole text as one block if no headers found

        logger.debug(f"Identified {len(grant_blocks)} potential grant blocks using regex split.")

        for block in grant_blocks:
            if len(block.strip()) < 50: continue # Skip very short blocks

            grant = {}
            block_lower = block.lower()

            # Extract Title (more flexible)
            title_match = re.search(r'(?:\*\*|##|grant(?: name)?|title):?\s*"?([^"\n(]{10,150}?)"?\s*(?:\(|\n|Source:|Deadline:)', block, re.IGNORECASE)
            if title_match:
                grant["title"] = title_match.group(1).strip()
            else: # Fallback: Use first significant line if it looks like a title
                first_lines = [line.strip() for line in block.strip().split('\n') if line.strip()]
                if first_lines and len(first_lines[0]) > 5 and len(first_lines[0]) < 150 and not first_lines[0].startswith(('http', 'Source:', 'Deadline:')):
                    grant["title"] = first_lines[0]
                # else: continue # Skip block if no title found?

            # Extract Source URL (crucial)
            url_match = re.search(r'(?:url|link|source|website|more info):?\s*(https?://[^\s'")]+)', block, re.IGNORECASE)
            if url_match:
                grant["source_url"] = url_match.group(1).strip()
            # else: continue # Skip if no URL found?

            # Extract Description (capture more text)
            desc_match = re.search(r'(?:description|overview|summary|details):?\s*((?:.|\n)+?)(?:\n\s*(?:Deadline|Amount|Eligibility|Source:|URL:|Link:)|$)', block, re.IGNORECASE)
            if desc_match:
                grant["description"] = re.sub(r'\n\s*\n', '\n', desc_match.group(1).strip()) # Clean up extra newlines
            elif grant.get("title"): # Fallback: Use text after title if no description marker
                 desc_start_index = block.find(grant["title"]) + len(grant["title"])
                 potential_desc = block[desc_start_index:].strip()
                 # Take text until the next potential field marker
                 end_match = re.search(r'\n\s*(?:Deadline|Amount|Eligibility|Source:|URL:|Link:)', potential_desc, re.IGNORECASE)
                 if end_match:
                     grant["description"] = potential_desc[:end_match.start()].strip()
                 else:
                     grant["description"] = potential_desc
            else:
                 grant["description"] = block.strip()

            # Extract Deadline
            deadline_match = re.search(r'(?:deadline|due(?: date)?|applications due|closes on|submit by):?\s*([^\n(]{5,40}?)(?:\(|\n|Amount:|Eligibility:)', block, re.IGNORECASE)
            if deadline_match:
                grant["deadline"] = deadline_match.group(1).strip()

            # Extract Amount
            amount_match = re.search(r'(?:amount|funding(?: available)?|award(?: amount)?|grant size):?\s*([^\n(]{5,50}?)(?:\(|\n|Eligibility:|Deadline:)', block, re.IGNORECASE)
            if amount_match:
                grant["amount"] = amount_match.group(1).strip()

            # Extract Eligibility
            elig_match = re.search(r'(?:eligibility|eligible applicants|who can apply):?\s*((?:.|\n)+?)(?:\n\s*(?:Amount:|Deadline:|Source:|URL:|Link:)|$)', block, re.IGNORECASE)
            if elig_match:
                grant["eligibility"] = re.sub(r'\n\s*\n', '\n', elig_match.group(1).strip()) # Clean up

            # Extract Source Name
            source_match = re.search(r'(?:source|provider|funder|agency):\s*([^\n]+)', block, re.IGNORECASE)
            if source_match:
                grant["source_name"] = source_match.group(1).strip()
            elif grant.get("source_url") and grant["source_url"].startswith("http"):
                try:
                    domain = urlparse(grant["source_url"]).netloc
                    grant["source_name"] = domain.replace("www.", "").split(".")[-2].capitalize() # Simple extraction
                except Exception: pass
            else:
                 grant["source_name"] = "Unknown Source"

            # Add grant if essential fields are present
            if grant.get("title") and grant.get("description") and grant.get("source_url"):
                logger.debug(f"Regex extracted grant: {grant.get('title')}")
                grants.append(grant)
            else:
                 logger.debug(f"Skipping block, missing essential fields. Block start: {block[:100]}...")

        return grants

    def _parse_deadline_flexible(self, deadline_str):
        """Attempt to parse various deadline string formats."""
        if not deadline_str or not isinstance(deadline_str, str):
             return None

        # Common date formats
        formats = [
            "%B %d, %Y", # March 31, 2025
            "%b %d, %Y", # Mar 31, 2025
            "%m/%d/%Y", # 03/31/2025
            "%Y-%m-%d", # 2025-03-31
            "%d %B %Y", # 31 March 2025
            "%d %b %Y", # 31 Mar 2025
            "%Y/%m/%d", # 2025/03/31
        ]

        # Normalize string: remove extra spaces, common phrases
        clean_str = deadline_str.strip()
        clean_str = re.sub(r'\s*\(.*?\)', '', clean_str) # Remove text in parentheses
        clean_str = re.sub(r'at\s+\d{1,2}:\d{2}\s*(?:AM|PM)?(?:\s+\w+)?', '', clean_str, flags=re.IGNORECASE).strip() # Remove time

        for fmt in formats:
            try:
                return datetime.strptime(clean_str, fmt)
            except ValueError:
                continue

        # Handle relative terms or ongoing
        if "ongoing" in clean_str.lower() or "rolling" in clean_str.lower():
            # Represent rolling/ongoing with a far future date?
            return datetime.now() + timedelta(days=365*5) # Arbitrary 5 years in future
        if "none" in clean_str.lower() or "n/a" in clean_str.lower():
             return None

        logger.warning(f"Could not parse deadline string: '{deadline_str}'")
        return None # Return None if parsing fails

# Example usage (for testing)
if __name__ == '__main__':
    print("Testing Perplexity Client...")
    try:
        client = PerplexityClient()
        if client.is_available():
            test_query = "grant opportunities for rural broadband deployment"
            print(f"Performing deep search for: '{test_query}'")
            results = client.deep_search(test_query, site_restrictions=["rd.usda.gov", "grants.gov"])

            if results and "error" not in results:
                print("Search successful. Attempting to extract grants...")
                extracted_grants = client.extract_grant_data(results)
                print(f"Extracted {len(extracted_grants)} grants.")
                if extracted_grants:
                    print("\nFirst extracted grant:")
                    print(json.dumps(extracted_grants[0], indent=2, default=str))
            else:
                print(f"Search failed or returned error: {results.get('error')}")
        else:
             print("Perplexity client is not available. Check API key.")
    except Exception as e:
         print(f"An error occurred during testing: {e}")
