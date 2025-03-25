import requests
from bs4 import BeautifulSoup
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import re
from dateutil import parser

class GrantScraper:
    def __init__(self):
        """Initialize the grant scraper with common headers and configurations."""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
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