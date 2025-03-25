import logging
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import requests
import time
import re
import urllib.parse

logger = logging.getLogger(__name__)

class LouisianaGrantScraper:
    """Scraper for Louisiana state-specific grant opportunities."""
    
    def __init__(self):
        """Initialize the Louisiana grant scraper."""
        self.state_portals = [
            "https://www.opportunitylouisiana.gov/business-incentives/grants",
            "https://www.louisiana.gov/grants-and-projects/",
            "https://www.lsbdc.org/grants",
            "https://www.ladeltacorps.org/apply",
            "https://www.rurallouisiana.org/grants-and-loans"
        ]
        
        # Set up scraping session with headers
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        })
        
        logging.info("Louisiana grant scraper initialized")
    
    def scrape_grants(self, geo_focus="LA-08", max_grants=20):
        """
        Scrape Louisiana state websites for grants with a specific geographical focus.
        
        Args:
            geo_focus (str): Geographical area to focus on, e.g., "LA-08"
            max_grants (int): Maximum number of grants to return
            
        Returns:
            list: List of grant dictionaries
        """
        grants = []
        
        for portal in self.state_portals:
            try:
                logging.info(f"Scraping grants from: {portal}")
                response = self.session.get(portal, timeout=30)
                
                if response.status_code != 200:
                    logging.warning(f"Failed to access {portal}: Status code {response.status_code}")
                    continue
                
                # Parse HTML with BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract grant listings based on different site structures
                portal_grants = self._extract_grants_from_portal(soup, portal, geo_focus)
                
                if portal_grants:
                    logging.info(f"Found {len(portal_grants)} grants from {portal}")
                    grants.extend(portal_grants)
                else:
                    logging.info(f"No grants found from {portal}")
                
                # Respect site's crawl delay
                time.sleep(3)
                
            except Exception as e:
                logging.error(f"Error scraping {portal}: {str(e)}")
                continue
        
        # Sort by relevance (exact geo matches first)
        sorted_grants = sorted(grants, 
                               key=lambda g: (
                                   1 if self._exact_geo_match(g, geo_focus) else 0,
                                   g.get('relevance_score', 0)
                               ), 
                               reverse=True)
        
        return sorted_grants[:max_grants]
    
    def _extract_grants_from_portal(self, soup, portal_url, geo_focus):
        """Extract grants from a portal based on the site's structure."""
        grants = []
        
        # Extract grants based on different site structures
        if "opportunitylouisiana.gov" in portal_url:
            grants = self._extract_opportunity_louisiana_grants(soup, portal_url, geo_focus)
        elif "louisiana.gov" in portal_url:
            grants = self._extract_main_louisiana_grants(soup, portal_url, geo_focus)
        elif "lsbdc.org" in portal_url:
            grants = self._extract_lsbdc_grants(soup, portal_url, geo_focus)
        else:
            # Generic extraction for other portals
            grants = self._extract_generic_grants(soup, portal_url, geo_focus)
        
        return grants
    
    def _extract_opportunity_louisiana_grants(self, soup, portal_url, geo_focus):
        """Extract grants from opportunitylouisiana.gov portal."""
        grants = []
        
        # Look for grant cards/sections
        grant_sections = soup.select('.incentive-list .incentive-item, .grant-item, .card')
        
        for section in grant_sections:
            try:
                # Extract title
                title_elem = section.select_one('h2, h3, .card-title, .title')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Extract link
                link_elem = section.select_one('a')
                link = link_elem['href'] if link_elem and 'href' in link_elem.attrs else None
                
                # Make sure link is absolute
                if link and not link.startswith('http'):
                    link = urllib.parse.urljoin(portal_url, link)
                
                # Extract description
                desc_elem = section.select_one('.description, .content, .card-text, p')
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                
                # Only include if it matches geo focus
                if not self._matches_geo_focus(title + " " + description, geo_focus):
                    continue
                
                # Create grant entry
                grant = {
                    'title': title,
                    'description': description,
                    'source_url': link if link else portal_url,
                    'source_name': 'Louisiana Economic Development',
                    'category': 'state',
                    'relevance_score': 0.90 if self._exact_geo_match(title + " " + description, geo_focus) else 0.85
                }
                
                grants.append(grant)
                
            except Exception as e:
                logging.error(f"Error extracting grant from opportunitylouisiana.gov: {str(e)}")
                continue
        
        return grants
    
    def _extract_main_louisiana_grants(self, soup, portal_url, geo_focus):
        """Extract grants from main louisiana.gov portal."""
        grants = []
        
        # Look for grant listings
        grant_sections = soup.select('.grant-listing, article, .listing-item, .content-block')
        
        for section in grant_sections:
            try:
                # Extract title
                title_elem = section.select_one('h2, h3, h4, .title')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Extract link
                link_elem = section.select_one('a')
                link = link_elem['href'] if link_elem and 'href' in link_elem.attrs else None
                
                # Make sure link is absolute
                if link and not link.startswith('http'):
                    link = urllib.parse.urljoin(portal_url, link)
                
                # Extract description
                desc_elem = section.select_one('p, .description, .excerpt')
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                
                # Only include if it matches geo focus
                if not self._matches_geo_focus(title + " " + description, geo_focus):
                    continue
                
                # Create grant entry
                grant = {
                    'title': title,
                    'description': description,
                    'source_url': link if link else portal_url,
                    'source_name': 'Louisiana Government',
                    'category': 'state',
                    'relevance_score': 0.90 if self._exact_geo_match(title + " " + description, geo_focus) else 0.85
                }
                
                grants.append(grant)
                
            except Exception as e:
                logging.error(f"Error extracting grant from louisiana.gov: {str(e)}")
                continue
        
        return grants
    
    def _extract_lsbdc_grants(self, soup, portal_url, geo_focus):
        """Extract grants from Louisiana Small Business Development Center portal."""
        grants = []
        
        # Look for grant cards or sections
        grant_sections = soup.select('.grant-card, .resource-item, article, .card')
        
        for section in grant_sections:
            try:
                # Extract title
                title_elem = section.select_one('h2, h3, h4, .title, .card-title')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Extract link
                link_elem = section.select_one('a')
                link = link_elem['href'] if link_elem and 'href' in link_elem.attrs else None
                
                # Make sure link is absolute
                if link and not link.startswith('http'):
                    link = urllib.parse.urljoin(portal_url, link)
                
                # Extract description
                desc_elem = section.select_one('p, .description, .excerpt, .card-text')
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                
                # Only include if it matches geo focus
                if not self._matches_geo_focus(title + " " + description, geo_focus):
                    continue
                
                # Create grant entry
                grant = {
                    'title': title,
                    'description': description,
                    'source_url': link if link else portal_url,
                    'source_name': 'LSBDC',
                    'category': 'state',
                    'relevance_score': 0.90 if self._exact_geo_match(title + " " + description, geo_focus) else 0.85
                }
                
                grants.append(grant)
                
            except Exception as e:
                logging.error(f"Error extracting grant from LSBDC: {str(e)}")
                continue
        
        return grants
    
    def _extract_generic_grants(self, soup, portal_url, geo_focus):
        """Generic grant extraction for other portals."""
        grants = []
        
        # Look for potential grant headers
        headers = soup.select('h2, h3, h4')
        
        for header in headers:
            try:
                title = header.get_text(strip=True)
                
                # Skip if doesn't look like a grant
                if not any(kw in title.lower() for kw in ['grant', 'funding', 'financial', 'opportunity']):
                    continue
                
                # Get description from following paragraph
                desc_elem = header.find_next('p')
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                
                # Get link if available
                link_elem = header.find_parent('a') or header.find_next('a')
                link = link_elem['href'] if link_elem and 'href' in link_elem.attrs else None
                
                # Make sure link is absolute
                if link and not link.startswith('http'):
                    link = urllib.parse.urljoin(portal_url, link)
                
                # Only include if it matches geo focus
                if not self._matches_geo_focus(title + " " + description, geo_focus):
                    continue
                
                # Create grant entry
                grant = {
                    'title': title,
                    'description': description,
                    'source_url': link if link else portal_url,
                    'source_name': self._extract_source_name(portal_url),
                    'category': 'state',
                    'relevance_score': 0.88 if self._exact_geo_match(title + " " + description, geo_focus) else 0.82
                }
                
                grants.append(grant)
                
            except Exception as e:
                logging.error(f"Error extracting generic grant: {str(e)}")
                continue
        
        return grants
    
    def _matches_geo_focus(self, text, geo_focus):
        """Check if text matches the geographical focus."""
        text = text.lower()
        
        # Define region terms for common Louisiana regions
        la_regions = {
            "LA-08": [
                "natchitoches", "central louisiana", "cenla", "la-08", "district 8",
                "rapides", "avoyelles", "catahoula", "natchitoches parish", "vernon parish",
                "grant parish", "lasalle parish", "winn parish"
            ],
            "LA-05": [
                "monroe", "alexandria", "la-05", "district 5", "northeast louisiana",
                "ouachita", "lincoln", "jackson", "morehouse", "richland"
            ]
        }
        
        # Get region terms for specified focus
        region_terms = la_regions.get(geo_focus, [geo_focus.lower()])
        
        # Add general state terms to increase matches
        region_terms.extend(["louisiana", "statewide", "rural", "economic development"])
        
        # Check if any term is in the text
        return any(term in text for term in region_terms)
    
    def _exact_geo_match(self, text, geo_focus):
        """Check if text has an exact match for the geographical focus."""
        text = text.lower()
        
        # Specific terms for exact matching
        exact_terms = {
            "LA-08": ["la-08", "district 8", "natchitoches parish", "cenla", "central louisiana"],
            "LA-05": ["la-05", "district 5", "northeast louisiana"]
        }
        
        # Get exact terms for the focus
        focus_terms = exact_terms.get(geo_focus, [geo_focus.lower()])
        
        # Check for exact match
        return any(term in text for term in focus_terms)
    
    def _extract_source_name(self, url):
        """Extract a source name from the URL."""
        try:
            domain = urllib.parse.urlparse(url).netloc
            
            if "opportunitylouisiana.gov" in domain:
                return "Louisiana Economic Development"
            elif "louisiana.gov" in domain:
                return "Louisiana Government"
            elif "lsbdc.org" in domain:
                return "LSBDC"
            elif "ladeltacorps.org" in domain:
                return "LA Delta Corps"
            elif "rurallouisiana.org" in domain:
                return "Rural Louisiana"
            else:
                # Extract from domain
                parts = domain.split('.')
                if len(parts) >= 2:
                    return parts[0].capitalize()
                return domain
                
        except Exception:
            return "Louisiana Grant Source" 