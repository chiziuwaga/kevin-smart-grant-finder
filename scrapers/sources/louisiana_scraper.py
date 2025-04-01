import requests
import logging
from bs4 import BeautifulSoup
import re
from datetime import datetime
from urllib.parse import urljoin # For handling relative URLs

logger = logging.getLogger(__name__)

class LouisianaGrantScraper:
    def __init__(self):
        # List of known Louisiana state/regional grant portals
        self.state_portals = [
            "https://www.opportunitylouisiana.gov/business-incentives/grants",
            "https://www.louisiana.gov/grants-and-projects/", # General state portal
            # Add Natchitoches specific economic development if available
            # Placeholder - requires finding the exact page: "https://natchitoches.la.gov/economic-development/grants",
            "https://www.ladeltacorps.org/apply" # Example regional org
            # Add more relevant state agency or regional development sites
        ]
        self.session = requests.Session()
        # Use a realistic User-Agent
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        logger.info("Louisiana Grant Scraper initialized.")

    def scrape_portal(self, portal_url):
        """Scrapes a single Louisiana portal for grant information."""
        grants = []
        logger.info(f"Scraping Louisiana portal: {portal_url}")
        try:
            response = self.session.get(portal_url, timeout=30)
            response.raise_for_status() # Check for HTTP errors
            soup = BeautifulSoup(response.text, 'lxml') # Use lxml parser

            # --- Find Grant Information --- 
            # This requires inspecting each portal's HTML structure.
            # Define potential selectors based on common patterns.
            potential_selectors = [
                ".grant-listing", ".funding-opportunity", "article.grant",
                ".views-row", # Common in Drupal views
                ".card-body", ".item-list li", # General list items
                "div[class*=grant]", "div[class*=funding]" # Class contains patterns
            ]

            grant_elements = []
            for selector in potential_selectors:
                found = soup.select(selector)
                if found:
                    logger.debug(f"Found {len(found)} potential elements using selector '{selector}' on {portal_url}")
                    # Crude check to avoid overly broad selectors matching everything
                    if len(found) < 50: # Adjust threshold as needed
                        grant_elements.extend(found)
                        # Maybe break if a good selector is found?

            if not grant_elements:
                 logger.warning(f"No grant elements found using standard selectors on {portal_url}. Analyzing general text.")
                 # Fallback: Analyze larger text blocks if specific selectors fail
                 # This is less reliable and needs careful parsing

            processed_urls = set()
            for elem in grant_elements:
                try:
                    grant = {}
                    # Extract Title (look for headings or prominent links)
                    title_elem = elem.select_one('h2, h3, h4, .grant-title, .field-name-title a, .node-title a')
                    if title_elem:
                        grant["title"] = title_elem.text.strip()
                    else: # Fallback to link text if no heading
                         link_elem = elem.find('a', href=True)
                         if link_elem and len(link_elem.text.strip()) > 5:
                              grant["title"] = link_elem.text.strip()
                         else:
                              continue # Skip if no title

                    # Extract URL (find the primary link)
                    link_elem = elem.find('a', href=True)
                    if link_elem:
                        grant_url = link_elem['href']
                        # Make URL absolute
                        grant["source_url"] = urljoin(portal_url, grant_url)
                        if grant["source_url"] in processed_urls:
                            continue # Skip duplicate URL within the same page
                        processed_urls.add(grant["source_url"])
                    else:
                         grant["source_url"] = portal_url # Fallback to portal URL if no specific link

                    # Extract Description/Summary
                    desc_elem = elem.select_one('.grant-summary, .field-name-body, .description, p')
                    if desc_elem:
                        grant["description"] = desc_elem.text.strip()
                    else: # Combine text from paragraph tags
                        grant["description"] = ' '.join(p.text.strip() for p in elem.find_all('p'))

                    # Try to find Deadline and Amount (often harder with scraping)
                    grant["deadline"] = self._find_date_in_element(elem)
                    grant["amount"] = self._find_amount_in_element(elem)

                    # Static fields
                    grant["source_name"] = self._extract_source_name(portal_url)
                    grant["category"] = "state_grant"
                    grant["eligibility"] = "See grant details" # Assume default

                    # Basic validation
                    if grant.get("title") and grant.get("description") and grant.get("source_url"):
                         logger.debug(f"Scraped grant: {grant['title']} from {portal_url}")
                         grants.append(grant)

                except Exception as parse_err:
                     logger.error(f"Error parsing element on {portal_url}: {parse_err}", exc_info=True)
                     logger.debug(f"Problematic element snippet: {str(elem)[:200]}...")

        except requests.exceptions.RequestException as e:
            logger.error(f"Error accessing portal {portal_url}: {str(e)}")
        except Exception as e:
             logger.error(f"Unexpected error scraping portal {portal_url}: {str(e)}", exc_info=True)

        logger.info(f"Found {len(grants)} potential grants on {portal_url}")
        return grants

    def _find_date_in_element(self, element):
        """Attempt to find a date within the element's text using regex."""
        # Regex patterns for dates (add more as needed)
        date_patterns = [
            r'(?:deadline|due|closes(?: on)?):?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})', # Month D, YYYY
            r'(?:deadline|due|closes(?: on)?):?\s*(\d{1,2}/\d{1,2}/\d{4})', # MM/DD/YYYY
            r'(?:deadline|due|closes(?: on)?):?\s*(\d{4}-\d{2}-\d{2})' # YYYY-MM-DD
        ]
        text = element.get_text(separator=' ')
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                # Attempt to parse the date string
                try:
                    # Add more formats if needed for parsing
                    formats = ["%B %d, %Y", "%b %d, %Y", "%m/%d/%Y", "%Y-%m-%d"]
                    for fmt in formats:
                        try: return datetime.strptime(date_str, fmt)
                        except ValueError: pass
                    logger.warning(f"Found date string '{date_str}' but failed to parse.")
                    return date_str # Return raw string if parsing fails
                except Exception:
                     return date_str # Return raw string on error
        return None # No date found

    def _find_amount_in_element(self, element):
         """Attempt to find a monetary amount within the element's text."""
         # Regex patterns for amounts
         amount_patterns = [
             r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', # $1,000,000.00 or $5000
             r'(?:up to|funding(?: of)?)\s+\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
         ]
         text = element.get_text(separator=' ')
         for pattern in amount_patterns:
             match = re.search(pattern, text, re.IGNORECASE)
             if match:
                 amount_str = match.group(1).replace(',','') # Get number string
                 try:
                     # Convert to float or int if possible
                     return float(amount_str) if '.' in amount_str else int(amount_str)
                 except ValueError:
                     logger.warning(f"Found amount string '{match.group(1)}' but failed to convert.")
                     return match.group(1) # Return raw matched number string
         return None

    def _extract_source_name(self, url):
        """Extract a readable source name from the portal URL."""
        try:
            domain = urlparse(url).netloc
            domain = domain.replace("www.", "")
            # Basic cleanup - replace dashes, capitalize
            name = domain.split('.')[-2].replace('-', ' ').title()
            return f"Louisiana ({name})"
        except Exception:
            return "Louisiana State Portal"

    def scrape_all_portals(self):
        """Scrapes all configured Louisiana portals."""
        all_grants = []
        for portal in self.state_portals:
            grants_from_portal = self.scrape_portal(portal)
            all_grants.extend(grants_from_portal)
        logger.info(f"Completed scraping all Louisiana portals. Total grants found: {len(all_grants)}")
        return all_grants

# Example usage (for testing)
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    scraper = LouisianaGrantScraper()
    print("Scraping all configured Louisiana portals...")
    scraped_grants = scraper.scrape_all_portals()
    print(f"\n--- Found {len(scraped_grants)} Total Grants ---")
    for i, grant in enumerate(scraped_grants[:5]): # Print first 5
        print(f"\nGrant {i+1}:")
        print(f"  Title: {grant.get('title')}")
        print(f"  Source: {grant.get('source_name')}")
        print(f"  URL: {grant.get('source_url')}")
        print(f"  Deadline: {grant.get('deadline')}")
        print(f"  Amount: {grant.get('amount')}")
        print(f"  Description: {grant.get('description', '')[:100]}...")
