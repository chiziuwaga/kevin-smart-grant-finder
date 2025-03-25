import logging
from datetime import datetime
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class LouisianaGrantScraper:
    def __init__(self):
        """Initialize Louisiana grant scraper with source configurations."""
        self.state_portals = [
            {
                "url": "https://www.doa.la.gov/Pages/osp/Index.aspx",
                "name": "Office of State Procurement",
                "selectors": {
                    "grants": ".grant-opportunity",
                    "title": ".grant-title",
                    "deadline": ".deadline-date",
                    "description": ".grant-description"
                }
            },
            {
                "url": "https://www.opportunities.la.gov",
                "name": "Louisiana Opportunities",
                "selectors": {
                    "grants": ".opportunity-item",
                    "title": ".opp-title",
                    "deadline": ".opp-deadline",
                    "description": ".opp-description"
                }
            },
            {
                "url": "https://www.lcd.la.gov/public-notices-and-rfps/",
                "name": "Louisiana Community Development",
                "selectors": {
                    "grants": ".notice-item",
                    "title": ".notice-title",
                    "deadline": ".notice-date",
                    "description": ".notice-content"
                }
            }
        ]
        
        # LA-08 specific regions and keywords
        self.target_regions = [
            "Alexandria", "Vernon", "Rapides", "Grant",
            "Winn", "La Salle", "Caldwell", "Catahoula",
            "Concordia", "Avoyelles", "LA-08", "District 8"
        ]
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def scrape_grants(self) -> List[Dict]:
        """Scrape grants from all configured Louisiana portals.

        Returns:
            List[Dict]: List of grant opportunities.
        """
        all_grants = []
        
        for portal in self.state_portals:
            try:
                grants = self._scrape_portal(portal)
                all_grants.extend(grants)
                logging.info(f"Successfully scraped {len(grants)} grants from {portal['name']}")
            except Exception as e:
                logging.error(f"Error scraping {portal['name']}: {e}")
                continue
        
        # Filter for LA-08 relevant grants
        relevant_grants = [
            grant for grant in all_grants
            if self._is_relevant_to_la08(grant["description"])
        ]
        
        return relevant_grants

    def _scrape_portal(self, portal: Dict) -> List[Dict]:
        """Scrape grants from a specific portal.

        Args:
            portal (Dict): Portal configuration.

        Returns:
            List[Dict]: List of grants from the portal.
        """
        grants = []
        try:
            response = self.session.get(portal["url"], timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try primary selectors
            grant_elements = soup.select(portal["selectors"]["grants"])
            
            # Fallback to alternative patterns if no results
            if not grant_elements:
                grant_elements = self._find_grants_alternative(soup)
            
            for element in grant_elements:
                grant = self._extract_grant_info(element, portal)
                if grant:
                    grants.append(grant)
                    
        except Exception as e:
            logging.error(f"Error in portal scraping: {e}")
            raise
            
        return grants

    def _find_grants_alternative(self, soup: BeautifulSoup) -> List:
        """Find grant opportunities using alternative patterns.

        Args:
            soup (BeautifulSoup): Parsed HTML.

        Returns:
            List: List of elements that might be grants.
        """
        elements = []
        
        # Common patterns for grant listings
        patterns = [
            ".grant", ".funding", ".opportunity",
            "div[id*=grant]", "div[id*=funding]",
            "table tr", ".post", ".notice"
        ]
        
        for pattern in patterns:
            elements.extend(soup.select(pattern))
        
        return elements

    def _extract_grant_info(self, element: BeautifulSoup, portal: Dict) -> Optional[Dict]:
        """Extract grant information from an HTML element.

        Args:
            element (BeautifulSoup): HTML element containing grant info.
            portal (Dict): Portal configuration.

        Returns:
            Optional[Dict]: Extracted grant information or None if invalid.
        """
        try:
            # Try primary selectors
            title = element.select_one(portal["selectors"]["title"])
            deadline = element.select_one(portal["selectors"]["deadline"])
            description = element.select_one(portal["selectors"]["description"])
            
            # Fallback to text content if selectors fail
            title_text = title.get_text(strip=True) if title else element.find(text=True, recursive=False)
            desc_text = description.get_text(strip=True) if description else element.get_text(strip=True)
            
            if not title_text or not desc_text:
                return None
                
            # Parse deadline if available
            deadline_date = None
            if deadline:
                deadline_text = deadline.get_text(strip=True)
                try:
                    deadline_date = datetime.strptime(deadline_text, "%m/%d/%Y")
                except ValueError:
                    pass
            
            return {
                "title": title_text,
                "description": desc_text,
                "deadline": deadline_date,
                "source": portal["name"],
                "source_url": portal["url"],
                "scraped_at": datetime.utcnow(),
                "category": "state"
            }
            
        except Exception as e:
            logging.error(f"Error extracting grant info: {e}")
            return None

    def _is_relevant_to_la08(self, text: str) -> bool:
        """Check if text is relevant to LA-08 district.

        Args:
            text (str): Text to check.

        Returns:
            bool: True if relevant to LA-08.
        """
        text = text.lower()
        region_terms = [region.lower() for region in self.target_regions]
        return any(term in text for term in region_terms)