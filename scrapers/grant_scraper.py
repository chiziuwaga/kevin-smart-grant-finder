import os
import aiohttp
import logging
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re
from dateutil import parser
from api.perplexity_client import PerplexityClient
from database.mongodb_client import MongoDBClient
from database.pinecone_client import PineconeClient

class GrantScraper:
    def __init__(self, use_mock: bool = True):
        """Initialize grant scraper with necessary clients."""
        self.use_mock = use_mock
        if not use_mock:
            self.perplexity = PerplexityClient()
            self.mongodb = MongoDBClient()
            self.pinecone = PineconeClient()
            
            # API keys for various grant sources
            self.grants_gov_key = os.getenv("GRANTS_GOV_API_KEY")
            self.usda_key = os.getenv("USDA_API_KEY")
            self.ntia_key = os.getenv("NTIA_API_KEY")
            self.fcc_key = os.getenv("FCC_API_KEY")
            
            self.session = None
        else:
            self._setup_mock_data()
    
    def _setup_mock_data(self):
        """Set up mock data for development."""
        self.mock_grants = [
            {
                "title": "Rural Broadband Infrastructure Grant",
                "description": "Funding for rural broadband deployment in underserved areas",
                "url": "https://example.com/grants/1",
                "source": "grants.gov",
                "deadline": datetime.now() + timedelta(days=30),
                "amount": 500000,
                "category": "telecom",
                "agency": "FCC"
            },
            {
                "title": "Digital Literacy Program Grant",
                "description": "Support for nonprofit organizations providing digital literacy training",
                "url": "https://example.com/grants/2",
                "source": "usda.gov",
                "deadline": datetime.now() + timedelta(days=45),
                "amount": 250000,
                "category": "nonprofit",
                "agency": "USDA"
            },
            {
                "title": "Community Internet Access Initiative",
                "description": "Funding for community-based internet access points",
                "url": "https://example.com/grants/3",
                "source": "ntia.gov",
                "deadline": datetime.now() + timedelta(days=60),
                "amount": 750000,
                "category": "telecom",
                "agency": "NTIA"
            }
        ]
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def scrape_all_sources(self, query: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Scrape grants from all configured sources."""
        if self.use_mock:
            filtered_grants = self.mock_grants.copy()
            
            # Apply text search if provided
            if query:
                filtered_grants = [
                    g for g in filtered_grants 
                    if query.lower() in g["title"].lower() 
                    or query.lower() in g["description"].lower()
                ]
            
            # Apply category filter if provided
            if filters and "category" in filters and filters["category"] != "All":
                filtered_grants = [
                    g for g in filtered_grants 
                    if g["category"] == filters["category"]
                ]
            
            return {
                "grants": filtered_grants,
                "total_found": len(filtered_grants),
                "source_breakdown": self._calculate_source_breakdown(filtered_grants)
            }
        else:
            tasks = [
                self.scrape_grants_gov(query, filters),
                self.scrape_usda_grants(query, filters),
                self.scrape_ntia_grants(query, filters),
                self.scrape_fcc_grants(query, filters),
                self.search_perplexity(query, filters)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Combine and deduplicate results
            combined_grants = []
            seen_urls = set()
            
            for source_results in results:
                if isinstance(source_results, Exception):
                    logging.error(f"Error scraping source: {str(source_results)}")
                    continue
                    
                for grant in source_results.get("grants", []):
                    if grant["url"] not in seen_urls:
                        seen_urls.add(grant["url"])
                        combined_grants.append(grant)
            
            return {
                "grants": combined_grants,
                "total_found": len(combined_grants),
                "source_breakdown": self._calculate_source_breakdown(combined_grants)
            }
    
    async def scrape_grants_gov(self, query: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Scrape grants from Grants.gov API.
        
        Args:
            query (str): Search query
            filters (Optional[Dict]): Search filters
            
        Returns:
            Dict[str, Any]: Scraped grants and metadata
        """
        if not self.grants_gov_key:
            return {"grants": [], "error": "Grants.gov API key not configured"}
        
        headers = {"X-API-KEY": self.grants_gov_key}
        params = {
            "keywords": query,
            "grant_status": "posted",
        }
        
        if filters:
            params.update(filters)
        
        try:
            async with self.session.get(
                "https://www.grants.gov/grantsws/rest/opportunities/search",
                headers=headers,
                params=params
            ) as response:
                data = await response.json()
                return self._process_grants_gov_response(data)
        except Exception as e:
            logging.error(f"Error scraping Grants.gov: {str(e)}")
            return {"grants": [], "error": str(e)}
    
    async def scrape_usda_grants(self, query: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Scrape grants from USDA API."""
        if not self.usda_key:
            return {"grants": [], "error": "USDA API key not configured"}
        
        # TODO: Implement USDA API integration
        return {"grants": [], "error": "USDA scraping not implemented"}
    
    async def scrape_ntia_grants(self, query: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Scrape grants from NTIA BroadbandUSA."""
        if not self.ntia_key:
            return {"grants": [], "error": "NTIA API key not configured"}
        
        # TODO: Implement NTIA API integration
        return {"grants": [], "error": "NTIA scraping not implemented"}
    
    async def scrape_fcc_grants(self, query: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Scrape grants from FCC Funding API."""
        if not self.fcc_key:
            return {"grants": [], "error": "FCC API key not configured"}
        
        # TODO: Implement FCC API integration
        return {"grants": [], "error": "FCC scraping not implemented"}
    
    async def search_perplexity(self, query: str, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """Search for grants using Perplexity API."""
        return await self.perplexity.search_grants(query, filters)
    
    def _process_grants_gov_response(self, data: Dict) -> Dict[str, Any]:
        """Process Grants.gov API response."""
        processed = {
            "grants": [],
            "total_found": 0
        }
        
        if "opportunities" in data:
            for opp in data["opportunities"]:
                grant = {
                    "title": opp.get("title", ""),
                    "description": opp.get("description", ""),
                    "url": f"https://www.grants.gov/view-opportunity.html?oppId={opp.get('id')}",
                    "source": "grants.gov",
                    "deadline": opp.get("closeDate"),
                    "amount": opp.get("awardCeiling"),
                    "category": opp.get("category", "other"),
                    "agency": opp.get("agency", {}).get("name", "")
                }
                
                processed["grants"].append(grant)
            
            processed["total_found"] = len(processed["grants"])
        
        return processed
    
    def _calculate_source_breakdown(self, grants: List[Dict]) -> Dict[str, int]:
        """Calculate breakdown of grants by source."""
        breakdown = {}
        for grant in grants:
            source = grant.get("source", "other")
            breakdown[source] = breakdown.get(source, 0) + 1
        return breakdown
    
    def _is_relevant_to_region(self, text: str) -> bool:
        """Check if the grant is relevant to Louisiana region (LA-08)."""
        la_keywords = [
            'louisiana', 'la-08', 'la-8', 'lake charles', 'lafayette',
            'alexandria', 'opelousas', 'crowley', 'eunice', 'jennings',
            'louisiana\'s 8th district', 'louisiana 8th congressional district'
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in la_keywords)
    
    def scrape_grants_gov(self, category: str = None) -> List[Dict[str, Any]]:
        """Scrape grants from Grants.gov."""
        grants = []
        base_url = "https://www.grants.gov/web/grants/search-grants.html"
        
        try:
            response = self.session.get(base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find grant opportunities
            grant_elements = soup.find_all('div', class_='grant-opportunity')
            
            for element in grant_elements:
                # Extract grant details
                title = element.find('h4', class_='grant-title').text.strip()
                description = element.find('div', class_='grant-description').text.strip()
                deadline_text = element.find('span', class_='deadline').text.strip()
                amount_text = element.find('span', class_='amount').text.strip()
                
                # Parse deadline
                try:
                    deadline = parser.parse(deadline_text)
                except:
                    deadline = None
                
                # Parse amount
                amount = re.sub(r'[^\d.]', '', amount_text)
                amount = float(amount) if amount else None
                
                # Create grant object
                grant = {
                    'title': title,
                    'description': description,
                    'deadline': deadline,
                    'amount': amount,
                    'source_name': 'Grants.gov',
                    'source_url': base_url,
                    'category': category or 'federal',
                    'relevance_score': 0  # Will be calculated later
                }
                
                # Only add if relevant to region
                if self._is_relevant_to_region(description):
                    grants.append(grant)
        
        except Exception as e:
            logging.error(f"Error scraping Grants.gov: {str(e)}")
        
        return grants
    
    def scrape_usda_grants(self) -> List[Dict[str, Any]]:
        """Scrape grants from USDA Rural Development."""
        grants = []
        base_url = "https://www.rd.usda.gov/programs-services/all-programs"
        
        try:
            response = self.session.get(base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find grant programs
            program_elements = soup.find_all('div', class_='program-item')
            
            for element in program_elements:
                # Extract program details
                title = element.find('h3', class_='program-title').text.strip()
                description = element.find('div', class_='program-description').text.strip()
                
                # Create grant object
                grant = {
                    'title': title,
                    'description': description,
                    'deadline': None,  # USDA often has rolling deadlines
                    'amount': None,    # Amount varies by project
                    'source_name': 'USDA Rural Development',
                    'source_url': base_url,
                    'category': 'federal',
                    'relevance_score': 0  # Will be calculated later
                }
                
                # Only add if relevant to region
                if self._is_relevant_to_region(description):
                    grants.append(grant)
        
        except Exception as e:
            logging.error(f"Error scraping USDA grants: {str(e)}")
        
        return grants
    
    def scrape_louisiana_grants(self) -> List[Dict[str, Any]]:
        """Scrape grants specific to Louisiana."""
        grants = []
        base_url = "https://www.doa.la.gov/Pages/ocd/cdbg/about_lcdbg.aspx"
        
        try:
            response = self.session.get(base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Find grant opportunities
            grant_elements = soup.find_all('div', class_='grant-opportunity')
            
            for element in grant_elements:
                # Extract grant details
                title = element.find('h3', class_='grant-title').text.strip()
                description = element.find('div', class_='grant-description').text.strip()
                deadline_text = element.find('span', class_='deadline').text.strip()
                
                # Parse deadline
                try:
                    deadline = parser.parse(deadline_text)
                except:
                    deadline = None
                
                # Create grant object
                grant = {
                    'title': title,
                    'description': description,
                    'deadline': deadline,
                    'amount': None,  # Amount varies by project
                    'source_name': 'Louisiana CDBG',
                    'source_url': base_url,
                    'category': 'state',
                    'relevance_score': 0  # Will be calculated later
                }
                
                grants.append(grant)
        
        except Exception as e:
            logging.error(f"Error scraping Louisiana grants: {str(e)}")
        
        return grants 