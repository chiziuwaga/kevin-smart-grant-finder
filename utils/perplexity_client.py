import os
import requests
import logging
import json
import re
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class PerplexityClient:
    def __init__(self, use_mock=True):
        """Initialize Perplexity API client for deep research."""
        if use_mock:
            self._setup_mock_data()
            logging.info("Using mock Perplexity for development")
            return
            
        self.api_key = os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("Perplexity API key not found in environment variables")
        
        self.base_url = "https://api.perplexity.ai"
        self.retry_attempts = 3
        
        logging.info("Perplexity client initialized")
    
    def _setup_mock_data(self):
        """Set up mock data for development."""
        self.mock_results = {
            "choices": [
                {
                    "message": {
                        "content": """
                        Here are several grant opportunities that match your search criteria:
                        
                        1. USDA Rural Broadband Access Loan and Loan Guarantee
                        Description: This program furnishes loans and loan guarantees to provide funds for the costs of construction, improvement, or acquisition of facilities and equipment needed to provide broadband service in eligible rural areas.
                        Deadline: December 31, 2025
                        Amount: $50,000 - $10,000,000
                        Eligibility: Nonprofit and for-profit entities, Indian tribes, state and local governments
                        URL: https://www.rd.usda.gov/programs-services/telecommunications-programs/rural-broadband-access-loan-and-loan-guarantee
                        
                        2. Women's Business Center Program
                        Description: The Women's Business Center Program provides grants to nonprofit organizations that provide business counseling, training, and mentoring to women entrepreneurs, especially those who are socially and economically disadvantaged.
                        Deadline: March 15, 2025
                        Amount: Up to $150,000 annually
                        Eligibility: Nonprofit organizations serving women entrepreneurs
                        URL: https://www.sba.gov/offices/headquarters/wbo/resources/9876543
                        """
                    }
                }
            ]
        }
        
        self.mock_extracted_grants = [
            {
                "title": "USDA Rural Broadband Access Loan and Loan Guarantee",
                "description": "This program furnishes loans and loan guarantees to provide funds for the costs of construction, improvement, or acquisition of facilities and equipment needed to provide broadband service in eligible rural areas.",
                "deadline": "December 31, 2025",
                "amount": "$50,000 - $10,000,000",
                "eligibility": "Nonprofit and for-profit entities, Indian tribes, state and local governments",
                "source_url": "https://www.rd.usda.gov/programs-services/telecommunications-programs/rural-broadband-access-loan-and-loan-guarantee",
                "source_name": "USDA",
                "category": "telecom"
            },
            {
                "title": "Women's Business Center Program",
                "description": "The Women's Business Center Program provides grants to nonprofit organizations that provide business counseling, training, and mentoring to women entrepreneurs, especially those who are socially and economically disadvantaged.",
                "deadline": "March 15, 2025",
                "amount": "Up to $150,000 annually",
                "eligibility": "Nonprofit organizations serving women entrepreneurs",
                "source_url": "https://www.sba.gov/offices/headquarters/wbo/resources/9876543",
                "source_name": "SBA",
                "category": "nonprofit"
            }
        ]
    
    def deep_search(self, query, site_restrictions=None, max_results=100):
        """Perform a deep search using Perplexity API."""
        if hasattr(self, 'mock_results'):
            return self.mock_results
            
        # Build complete search query with site restrictions
        complete_query = query
        if site_restrictions:
            site_query = " OR ".join(site_restrictions)
            complete_query = f"{query} ({site_query})"
        
        # Prepare request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "sonar-medium-online",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a specialized grant search assistant. Your task is to find detailed "
                        "information about grant opportunities, including deadlines, amounts, eligibility "
                        "requirements, and application processes. Extract specific information from search results "
                        "and present it in a structured format."
                    )
                },
                {
                    "role": "user",
                    "content": complete_query
                }
            ]
        }
        
        # Make request to Perplexity API with retry logic
        for attempt in range(self.retry_attempts):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=60  # 60-second timeout
                )
                response.raise_for_status()
                
                # Extract and return search results
                search_results = response.json()
                logging.info(f"Perplexity deep search completed for query: {query}")
                
                # Process results
                return search_results
                
            except requests.exceptions.RequestException as e:
                if attempt < self.retry_attempts - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logging.warning(f"Perplexity API request failed (attempt {attempt+1}). Retrying in {wait_time}s. Error: {str(e)}")
                    time.sleep(wait_time)
                else:
                    logging.error(f"Error in Perplexity deep search after {self.retry_attempts} attempts: {str(e)}")
                    return {"error": str(e)}
    
    def extract_grant_data(self, search_results):
        """Extract structured grant data from Perplexity search results."""
        if hasattr(self, 'mock_extracted_grants'):
            return self.mock_extracted_grants
            
        grants = []
        
        try:
            # Extract content from Perplexity response
            if "choices" in search_results and search_results["choices"]:
                content = search_results["choices"][0]["message"]["content"]
                
                # Use structured extraction approach
                extraction_data = {
                    "model": "gpt-4o",
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a grant data extraction assistant. Extract all grant opportunities from the "
                                "provided text as structured data. For each grant, include the following fields if available: "
                                "title, description, deadline, amount, eligibility, source_url, and source_name. "
                                "Format the response as a JSON array of objects with these fields. If a field is not available, "
                                "omit it or use null."
                            )
                        },
                        {
                            "role": "user",
                            "content": f"Extract grant data from the following text:\n\n{content}"
                        }
                    ],
                    "response_format": {"type": "json_object"}
                }
                
                # Use OpenAI API for extraction
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if not openai_api_key:
                    logging.error("OpenAI API key not found for grant data extraction")
                    return self._extract_grants_with_regex(content)
                
                headers = {
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json"
                }
                
                try:
                    extraction_response = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json=extraction_data,
                        timeout=30
                    )
                    extraction_response.raise_for_status()
                    
                    extraction_result = extraction_response.json()
                    if "choices" in extraction_result and extraction_result["choices"]:
                        extracted_content = extraction_result["choices"][0]["message"]["content"]
                        
                        try:
                            grant_data = json.loads(extracted_content)
                            if "grants" in grant_data:
                                grants = grant_data["grants"]
                            else:
                                grants = [grant_data]  # Handle different formats
                                
                            logging.info(f"Successfully extracted {len(grants)} grants from Perplexity results")
                            
                        except json.JSONDecodeError:
                            logging.warning("Failed to parse JSON from extraction response, falling back to regex")
                            grants = self._extract_grants_with_regex(content)
                            
                except Exception as e:
                    logging.error(f"Error using OpenAI for grant extraction: {str(e)}")
                    grants = self._extract_grants_with_regex(content)
                    
        except Exception as e:
            logging.error(f"Error extracting grant data from Perplexity results: {str(e)}")
            
        # Process and validate extracted grants
        processed_grants = []
        for grant in grants:
            if "title" in grant and grant["title"] and "description" in grant and grant["description"]:
                # Generate source_url if missing
                if "source_url" not in grant or not grant["source_url"]:
                    grant["source_url"] = f"perplexity_search_{hash(grant['title'])}"
                
                processed_grants.append(grant)
                
        logging.info(f"Processed {len(processed_grants)} valid grants from extracted data")
        return processed_grants
    
    def _extract_grants_with_regex(self, text):
        """Extract grant information using regex as a fallback method."""
        logging.info("Using regex fallback for grant extraction")
        grants = []
        
        # Look for grant sections in the text
        grant_sections = re.split(r'\n\s*\d+\.\s+|\n\s*•\s+|\n\s*-\s+', text)
        
        for section in grant_sections:
            if not section.strip():
                continue
                
            grant = {}
            
            # Extract title
            title_match = re.search(r'(?:Title|Name|Grant):\s*(.*?)(?:\n|$)', section, re.IGNORECASE)
            if title_match:
                grant["title"] = title_match.group(1).strip()
            else:
                # Try to use the first line as title
                first_line = section.split('\n')[0].strip()
                if first_line and len(first_line) < 150:  # Reasonable title length
                    grant["title"] = first_line
                else:
                    continue  # Skip if we can't find a title
            
            # Extract description
            desc_match = re.search(r'(?:Description|Overview|Summary):\s*(.*?)(?:\n\w+:|$)', section, re.DOTALL | re.IGNORECASE)
            if desc_match:
                grant["description"] = desc_match.group(1).strip()
            else:
                # Use everything not captured by other fields as description
                grant["description"] = section.strip()
            
            # Extract deadline
            deadline_match = re.search(r'(?:Deadline|Due Date|Applications Due|Closes):\s*(.*?)(?:\n|$)', section, re.IGNORECASE)
            if deadline_match:
                grant["deadline"] = deadline_match.group(1).strip()
            
            # Extract amount
            amount_match = re.search(r'(?:Amount|Funding|Award|Grant Size):\s*(.*?)(?:\n|$)', section, re.IGNORECASE)
            if amount_match:
                grant["amount"] = amount_match.group(1).strip()
            
            # Extract eligibility
            elig_match = re.search(r'(?:Eligibility|Who Can Apply|Eligible Applicants):\s*(.*?)(?:\n\w+:|$)', section, re.DOTALL | re.IGNORECASE)
            if elig_match:
                grant["eligibility"] = elig_match.group(1).strip()
            
            # Extract source URL
            url_match = re.search(r'(?:URL|Link|Source|Website|More Info):\s*(https?://\S+)', section, re.IGNORECASE)
            if url_match:
                grant["source_url"] = url_match.group(1).strip()
            else:
                # Generate a unique identifier based on the title
                grant["source_url"] = f"perplexity_extract_{hash(grant['title'])}"
            
            # Extract source name
            source_match = re.search(r'(?:Source|Provider|Funder|Agency):\s*(.*?)(?:\n|$)', section, re.IGNORECASE)
            if source_match:
                grant["source_name"] = source_match.group(1).strip()
            elif "source_url" in grant and grant["source_url"].startswith("http"):
                # Extract from URL
                from urllib.parse import urlparse
                domain = urlparse(grant["source_url"]).netloc
                grant["source_name"] = domain.replace("www.", "").split(".")[0].capitalize()
            
            # Only add grants with at least title, description and a unique identifier
            if "title" in grant and "description" in grant and "source_url" in grant:
                grants.append(grant)
        
        logging.info(f"Extracted {len(grants)} grants using regex method")
        return grants
