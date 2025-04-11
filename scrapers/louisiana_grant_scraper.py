"""
Louisiana-specific grant scraper for Smart Grant Finder.
Targets Louisiana state government websites and LA-08 district-specific funding opportunities.
"""

import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import time
import random
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)

class LouisianaGrantScraper:
    def __init__(self):
        """Initialize the Louisiana grant scraper with state-specific sources."""
        self.state_portals = [
            # Economic development sites
            "https://www.opportunitylouisiana.gov/business-incentives/grants",
            "https://www.louisiana.gov/grants-and-projects/",
            
            # District-specific sites
            "https://natchitoches.la.gov/departments/administration/economic-development/",
            "https://www.ladeltacorps.org/apply",
            
            # Small business sites
            "https://www.lsbdc.org/grants",
            "https://www.cabl.org/grants-and-resources/",
            
            # Arts & Culture
            "https://www.crt.state.la.us/cultural-development/arts/grants/",
            
            # Telecommunications specific
            "https://connect.la.gov/funding-opportunities/",
            "https://gumbo.ldaf.la.gov/gumbo-grant-program/",
            
            # Nonprofit & Women-owned business resources
            "https://www.wbec-south.org/grant-opportunities",
            "https://www.louisianasbdc.org/women-owned-business-resources/"
        ]
        
        # Initialize session with retry capability
        self.session = requests.Session()
        
        # Set headers to mimic a real browser
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5"
        })

    def scrape_la_grants(self, geo_focus="LA-08"):
        """
        Scrapes Louisiana state websites for grants with location-specific focus.
        
        Args:
            geo_focus: Geographic focus (e.g., "LA-08", "Natchitoches")
            
        Returns:
            List of grant dictionaries with standard format
        """
        grants = []
        
        logger.info(f"Starting Louisiana grant scraping for region: {geo_focus}")
        
        for portal in self.state_portals:
            try:
                # Random delay to avoid overwhelming servers (1-3 seconds)
                time.sleep(random.uniform(1, 3))
                
                logger.info(f"Scraping: {portal}")
                response = self.session.get(portal, timeout=30)
                
                # Check if request was successful
                if response.status_code != 200:
                    logger.warning(f"Failed to access {portal} - Status code: {response.status_code}")
                    continue
                
                # Parse HTML content
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract grant listings
                grant_elements = self._find_grant_elements(soup, portal)
                
                # Process each grant element
                for element in grant_elements:
                    grant = self._extract_grant_data(element, portal)
                    
                    # Only add grants that match geographic focus and have minimum required fields
                    if grant and self._matches_geo_focus(grant, geo_focus):
                        grants.append(grant)
                
                logger.info(f"Found {len(grant_elements)} potential grants at {portal}")
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error scraping {portal}: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error scraping {portal}: {str(e)}", exc_info=True)
        
        # Deduplicate grants by URL
        unique_grants = self._deduplicate_grants(grants)
        
        logger.info(f"Completed Louisiana scraping. Found {len(unique_grants)} unique grants matching criteria.")
        return unique_grants
    
    def _find_grant_elements(self, soup, portal_url):
        """
        Find grant elements using various selectors based on the portal structure.
        Uses multiple strategies to adapt to different website layouts.
        """
        elements = []
        
        # Common grant container selectors (covers most state websites)
        selectors = [
            '.grant-listing', '.funding-opportunity', 'article.grant', 
            '.grant-card', '.funding-item', '.opportunity-list-item',
            '.programs-list .program', '.resource-item', '.content-block'
        ]
        
        # Try each selector
        for selector in selectors:
            found = soup.select(selector)
            if found:
                elements.extend(found)
                logger.debug(f"Found {len(found)} elements with selector '{selector}'")
        
        # If standard selectors don't work, try pattern-based approaches
        if not elements:
            # Look for headers that might indicate grant sections
            headers = soup.select('h2, h3, h4, h5')
            
            for header in headers:
                grant_keywords = ['grant', 'fund', 'award', 'opportunity', 'program', 'assistance']
                
                # Check if header text contains grant-related keywords
                if any(keyword in header.text.lower() for keyword in grant_keywords):
                    # Get the container that might hold the grant details
                    container = self._get_content_container(header)
                    if container:
                        elements.append(container)
        
        # If still no elements, try extracting from entire page structure
        if not elements and soup.find('body'):
            logger.warning(f"Using fallback content extraction for {portal_url}")
            
            # Look for text blocks that might indicate grant information
            paragraphs = soup.select('p')
            for para in paragraphs:
                if len(para.text.strip()) > 100:  # Reasonably long paragraph
                    if any(keyword in para.text.lower() for keyword in ['grant', 'fund', 'apply', 'eligib']):
                        elements.append(para.parent)
        
        return elements
    
    def _get_content_container(self, header):
        """Get the container element that likely contains the full grant details."""
        # Try to get the parent container that encompasses all info
        container = header.parent
        
        # If the parent is too small, go up one more level
        if container and len(container.get_text(strip=True)) < 200:
            container = container.parent
            
        return container
    
    def _extract_grant_data(self, element, source_url):
        """
        Extract structured grant data from an HTML element.
        Handles various page formats and structures.
        """
        if not element:
            return None
            
        grant_data = {
            "source_url": source_url,
            "source_name": self._extract_source_name(source_url)
        }
        
        # Extract grant title
        grant_data["title"] = self._extract_title(element)
        if not grant_data["title"]:
            return None
            
        # Extract description
        grant_data["description"] = self._extract_description(element)
        if not grant_data["description"]:
            return None
            
        # Extract other fields
        grant_data["deadline"] = self._extract_deadline(element)
        grant_data["amount"] = self._extract_amount(element)
        grant_data["eligibility"] = self._extract_eligibility(element)
        
        # If we found a link specifically for this grant, update the source_url
        specific_url = self._extract_specific_url(element, source_url)
        if specific_url:
            grant_data["source_url"] = specific_url
        
        # Add Louisiana tags
        grant_data["category"] = "state_grant"
        grant_data["tags"] = ["Louisiana", "State Grant"]
        
        return grant_data
    
    def _extract_title(self, element):
        """Extract grant title from element."""
        # First look for heading elements
        for heading in element.select('h1, h2, h3, h4, h5'):
            title = heading.get_text(strip=True)
            if title and len(title) < 150:  # Reasonable title length
                return title
                
        # Otherwise look for emphasized text that might be a title
        for candidate in element.select('strong, b, em, i, .title, .heading'):
            title = candidate.get_text(strip=True)
            if title and len(title) < 150:
                return title
        
        # Fallback: use first non-empty text node
        text = element.get_text(strip=True)
        if text:
            # Extract first sentence or line as title
            lines = text.split('\n')
            for line in lines:
                if line.strip() and len(line) < 150:
                    return line.strip()
            
            # Or limit to first 100 chars
            return text[:100] + ('...' if len(text) > 100 else '')
        
        return None
    
    def _extract_description(self, element):
        """Extract grant description from element."""
        # Extract text from paragraph elements
        paragraphs = element.select('p')
        if paragraphs:
            description = ' '.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            if description:
                return description
                
        # If no paragraphs, extract text excluding the title elements
        title_elements = element.select('h1, h2, h3, h4, h5, strong, b')
        for title_el in title_elements:
            title_el.extract()  # Remove from DOM
            
        description = element.get_text(strip=True)
        return description if description else "No description available"
    
    def _extract_deadline(self, element):
        """Extract application deadline from element."""
        # Get text content
        text = element.get_text()
        
        # Regular expressions for different deadline formats
        patterns = [
            r'(?:deadline|due date|close[sd]? on|submission deadline|applications due)(?:\s*(?:is|by|on)?):?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',  # March 15, 2023
            r'(?:deadline|due date|close[sd]? on|submission deadline|applications due)(?:\s*(?:is|by|on)?):?\s*(\d{1,2}/\d{1,2}/\d{4})',  # 03/15/2023
            r'(?:deadline|due date|close[sd]? on|submission deadline|applications due)(?:\s*(?:is|by|on)?):?\s*(\d{1,2}-\d{1,2}-\d{4})',  # 03-15-2023
            r'(?:deadline|due date|close[sd]? on|submission deadline|applications due)(?:\s*(?:is|by|on)?):?\s*(\d{4}-\d{1,2}-\d{1,2})'   # 2023-03-15
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                deadline_str = match.group(1)
                try:
                    return self._parse_date(deadline_str)
                except ValueError:
                    continue
        
        # If no deadline found, set a default (30 days from now)
        return datetime.utcnow() + timedelta(days=30)
    
    def _parse_date(self, date_str):
        """Parse date string into datetime object, handling multiple formats."""
        formats = [
            '%B %d, %Y',  # March 15, 2023
            '%b %d, %Y',  # Mar 15, 2023
            '%m/%d/%Y',   # 03/15/2023
            '%m-%d-%Y',   # 03-15-2023
            '%Y-%m-%d'    # 2023-03-15
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
                
        # If all formats fail, raise error
        raise ValueError(f"Could not parse date: {date_str}")
    
    def _extract_amount(self, element):
        """Extract grant amount/funding information."""
        text = element.get_text()
        
        # Patterns for dollar amounts
        patterns = [
            r'(?:funding|amount|award|grant size)(?:\s*(?:is|of|:))?\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:thousand|k|million|m)?',  # $100,000
            r'(?:up to|maximum of|as much as)\s*\$?(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:thousand|k|million|m)?',  # up to $100,000
            r'\$(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:thousand|k|million|m)?(?:\s*(?:in|of|for))?\s*(?:funding|grants|awards)'  # $100,000 in funding
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = match.group(1)
                
                # Check for thousand/million multipliers
                multiplier = 1
                if 'thousand' in text[match.start():match.end()] or 'k' in text[match.start():match.end()]:
                    multiplier = 1000
                elif 'million' in text[match.start():match.end()] or 'm' in text[match.start():match.end()]:
                    multiplier = 1000000
                
                # Remove commas and convert to float, then format with $ and commas
                try:
                    amount_value = float(amount.replace(',', '')) * multiplier
                    return f"${amount_value:,.2f}".replace('.00', '')
                except ValueError:
                    return amount
        
        return "Amount not specified"
    
    def _extract_eligibility(self, element):
        """Extract eligibility information."""
        text = element.get_text()
        
        # Patterns for eligibility sections
        patterns = [
            r'(?:eligible applicants|eligibility|who can apply|who should apply)[:\s]+(.*?)(?:\.(?:\s*[A-Z])|$|\n\n)',
            r'(?:this (?:grant|program|opportunity) is for)[:\s]+(.*?)(?:\.(?:\s*[A-Z])|$|\n\n)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                eligibility = match.group(1).strip()
                # Limit to a reasonable length
                if len(eligibility) > 500:
                    eligibility = eligibility[:497] + '...'
                return eligibility
        
        return "See grant details for eligibility information"
    
    def _extract_specific_url(self, element, base_url):
        """Extract a specific URL for the grant if available."""
        # Look for anchor tags that might link to the specific grant
        grant_link_texts = ['apply', 'learn more', 'details', 'application', 'more info']
        
        for anchor in element.select('a'):
            href = anchor.get('href')
            text = anchor.get_text(strip=True).lower()
            
            if href and any(link_text in text for link_text in grant_link_texts):
                # Handle relative URLs
                if not href.startswith(('http://', 'https://')):
                    href = urljoin(base_url, href)
                return href
                
        return None
    
    def _extract_source_name(self, url):
        """Extract organization name from URL."""
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Remove www. if present
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Extract organization name
            org_parts = domain.split('.')
            if len(org_parts) >= 2:
                # For .gov.XX domains (like louisiana.gov)
                if 'gov' in org_parts:
                    gov_index = org_parts.index('gov')
                    if gov_index > 0:
                        org_name = org_parts[gov_index-1]
                        return f"{org_name.title()} Government"
                    else:
                        return "Louisiana Government"
                else:
                    org_name = org_parts[0]
                    return org_name.title()
            
            return "Louisiana Government"
            
        except Exception:
            return "Louisiana Government"
    
    def _matches_geo_focus(self, grant, geo_focus):
        """
        Check if grant matches the geographical focus.
        This specifically handles LA-08 district and other Louisiana regions.
        """
        # LA regions mapping (focusing on LA-08 district)
        la_regions = {
            "LA-08": ["natchitoches", "central louisiana", "cenla", "la-08", 
                     "district 8", "rapides", "avoyelles", "catahoula", 
                     "concordia", "grant", "lasalle", "vernon", "winn"]
        }
        
        # Get region terms based on geo_focus
        region_terms = la_regions.get(geo_focus, [geo_focus.lower()])
        
        # Build combined text to search within
        combined_text = (
            grant.get("title", "") + " " + 
            grant.get("description", "") + " " + 
            grant.get("eligibility", "")
        ).lower()
        
        # Check for mentions of "statewide" which applies to all regions
        if "statewide" in combined_text or "all parishes" in combined_text:
            return True
            
        # Check for mentions of specific terms
        for term in region_terms:
            if term in combined_text:
                return True
                
        return False
    
    def _deduplicate_grants(self, grants):
        """
        Remove duplicate grants based on title similarity and URL.
        """
        unique_grants = {}
        
        for grant in grants:
            # Create a key based on URL or normalized title
            key = grant.get("source_url", "")
            if not key or key == "Amount not specified":
                # Normalize title by lowercase, remove spaces and punctuation
                title = grant.get("title", "").lower()
                title = re.sub(r'[^\w]', '', title)
                key = title
                
            # Keep the grant with the most complete information
            if key not in unique_grants or self._is_more_complete(grant, unique_grants[key]):
                unique_grants[key] = grant
                
        return list(unique_grants.values())
    
    def _is_more_complete(self, grant1, grant2):
        """Determine which grant record is more complete."""
        # Count non-empty fields to determine completeness
        count1 = sum(1 for key, value in grant1.items() 
                   if value and value not in ["Amount not specified", 
                                              "See grant details for eligibility information"])
        
        count2 = sum(1 for key, value in grant2.items() 
                   if value and value not in ["Amount not specified", 
                                              "See grant details for eligibility information"])
                                              
        return count1 > count2


if __name__ == "__main__":
    # Setup basic logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test the scraper
    scraper = LouisianaGrantScraper()
    grants = scraper.scrape_la_grants(geo_focus="LA-08")
    
    # Print results
    print(f"Found {len(grants)} grants")
    for i, grant in enumerate(grants, 1):
        print(f"\n--- Grant {i} ---")
        print(f"Title: {grant.get('title')}")
        print(f"Source: {grant.get('source_name')}")
        print(f"URL: {grant.get('source_url')}")
        print(f"Deadline: {grant.get('deadline')}")
        print(f"Amount: {grant.get('amount')}")
        print(f"-------------------") 