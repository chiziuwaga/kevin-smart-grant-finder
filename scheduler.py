import os
import logging
from datetime import datetime
import pytz
import time
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SchedulerConfig:
    """Scheduler configuration for Kevin's Smart Grant Finder."""
    
    def __init__(self):
        """Initialize scheduler configuration with values from environment."""
        self.timezone = pytz.timezone(os.getenv("TIMEZONE", "America/New_York"))
        self.schedule_days = os.getenv("SCHEDULE_DAYS", "monday,thursday").lower().split(",")
        self.schedule_time = os.getenv("SCHEDULE_TIME", "10:00")
        self.heroku_app = os.getenv("HEROKU_APP_NAME", "kevin-grant-finder")
        self.heroku_api_key = os.getenv("HEROKU_API_KEY")
        
        # Validate schedule days
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        self.schedule_days = [day.strip() for day in self.schedule_days if day.strip() in valid_days]
        
        if not self.schedule_days:
            self.schedule_days = ["monday", "thursday"]  # Default to Monday and Thursday
            logging.warning("No valid schedule days found. Defaulting to Monday and Thursday.")
    
    def get_cron_expression(self):
        """Convert schedule to cron expression format."""
        # Parse time HH:MM to get hour and minute
        try:
            hour, minute = self.schedule_time.split(":")
            hour, minute = int(hour), int(minute)
        except (ValueError, TypeError):
            logging.error(f"Invalid time format: {self.schedule_time}. Using 10:00 AM.")
            hour, minute = 10, 0
        
        # Map days to cron day-of-week numbers (0=Sunday, 1=Monday, ..., 6=Saturday)
        day_map = {
            "sunday": 0, "monday": 1, "tuesday": 2, "wednesday": 3, 
            "thursday": 4, "friday": 5, "saturday": 6
        }
        
        day_numbers = [str(day_map.get(day, 1)) for day in self.schedule_days]
        day_of_week = ",".join(day_numbers) if day_numbers else "1,4"  # Default to Mon,Thu (1,4)
        
        # Format: minute hour * * day_of_week
        return f"{minute} {hour} * * {day_of_week}"
    
    def configure_cron_to_go(self):
        """Configure Cron To Go addon in Heroku for scheduled job execution."""
        if not self.heroku_api_key:
            logging.error("HEROKU_API_KEY not found in environment variables")
            return False
        
        # First, ensure Cron To Go addon is provisioned
        self._provision_cron_to_go()
        
        # Get cron expression
        cron_expression = self.get_cron_expression()
        logging.info(f"Generated cron expression: {cron_expression}")
        
        # Set up headers for Cron To Go API
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.heroku_api_key}"
        }
        
        # Get addon info to extract API endpoint
        try:
            addon_response = requests.get(
                f"https://api.heroku.com/apps/{self.heroku_app}/addons/crontogo",
                headers={
                    **headers,
                    "Accept": "application/vnd.heroku+json; version=3"
                }
            )
            addon_response.raise_for_status()
            
            # Extract Cron To Go API URL from config vars
            config_vars_url = addon_response.json().get("config_vars_url")
            if not config_vars_url:
                logging.error("Failed to get Cron To Go config vars URL")
                return False
                
            config_response = requests.get(
                config_vars_url,
                headers={
                    **headers,
                    "Accept": "application/vnd.heroku+json; version=3"
                }
            )
            config_response.raise_for_status()
            
            crontogo_api_key = config_response.json().get("CRONTOGO_API_KEY")
            if not crontogo_api_key:
                logging.error("Failed to get CRONTOGO_API_KEY")
                return False
            
            # Set up Cron To Go API headers
            crontogo_headers = {
                "Content-Type": "application/json",
                "X-CronToGo-API-Key": crontogo_api_key
            }
            
            # Check for existing jobs
            jobs_response = requests.get(
                "https://api.crontogo.com/jobs",
                headers=crontogo_headers
            )
            jobs_response.raise_for_status()
            
            # Find and update existing job or create new one
            job_data = {
                "command": "python run_grant_search.py",
                "schedule": cron_expression,
                "timezone": self.timezone.zone
            }
            
            existing_jobs = jobs_response.json()
            grant_search_job = next((job for job in existing_jobs if "grant_search" in job.get("command", "")), None)
            
            if grant_search_job:
                # Update existing job
                job_id = grant_search_job["id"]
                update_response = requests.put(
                    f"https://api.crontogo.com/jobs/{job_id}",
                    headers=crontogo_headers,
                    json=job_data
                )
                update_response.raise_for_status()
                logging.info(f"Updated existing Cron To Go job: {job_id}")
            else:
                # Create new job
                create_response = requests.post(
                    "https://api.crontogo.com/jobs",
                    headers=crontogo_headers,
                    json=job_data
                )
                create_response.raise_for_status()
                job_id = create_response.json().get("id")
                logging.info(f"Created new Cron To Go job: {job_id}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error configuring Cron To Go: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logging.error(f"Response: {e.response.text}")
            return False
    
    def _provision_cron_to_go(self):
        """Ensure Cron To Go addon is provisioned for the Heroku app."""
        if not self.heroku_api_key:
            return False
            
        headers = {
            "Accept": "application/vnd.heroku+json; version=3",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.heroku_api_key}"
        }
        
        try:
            # Check if addon already exists
            addon_response = requests.get(
                f"https://api.heroku.com/apps/{self.heroku_app}/addons",
                headers=headers
            )
            addon_response.raise_for_status()
            
            addons = addon_response.json()
            crontogo_exists = any(addon.get("name", "").startswith("crontogo") for addon in addons)
            
            if not crontogo_exists:
                # Provision addon
                provision_response = requests.post(
                    f"https://api.heroku.com/apps/{self.heroku_app}/addons",
                    headers=headers,
                    json={"plan": "crontogo:free"}
                )
                
                if provision_response.status_code == 422:
                    # Try hobby plan if free plan failed
                    provision_response = requests.post(
                        f"https://api.heroku.com/apps/{self.heroku_app}/addons",
                        headers=headers,
                        json={"plan": "crontogo:hobby"}
                    )
                
                provision_response.raise_for_status()
                logging.info("Provisioned Cron To Go addon")
                
                # Wait for addon to be fully provisioned
                time.sleep(5)
                
            return True
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error provisioning Cron To Go: {str(e)}")
            if hasattr(e, 'response') and e.response:
                logging.error(f"Response: {e.response.text}")
            return False

class Scheduler:
    """Handles scheduling of grant search jobs."""
    
    def __init__(self):
        """Initialize the scheduler."""
        self.config = SchedulerConfig()
        logging.info(f"Scheduler initialized with days: {self.config.schedule_days}, time: {self.config.schedule_time}")
    
    def setup_heroku_scheduler(self):
        """Set up scheduling on Heroku using Cron To Go."""
        return self.config.configure_cron_to_go()
    
    def execute_scheduled_search(self, research_agent, analysis_agent):
        """Execute the grant search as a scheduled job."""
        from datetime import datetime
        
        logging.info(f"Starting scheduled grant search at {datetime.now()}")
        
        try:
            # Execute search for both domains
            telecom_params = {
                "category": "telecom",
                "search_terms": ["broadband deployment", "rural connectivity", "telecommunications infrastructure"],
                "funding_type": ["grant", "cooperative agreement"],
                "eligible_entities": ["nonprofits", "municipalities"],
                "geo_restrictions": "LA-08",
                "sources": ["Grants.gov", "USDA", "FCC", "NTIA BroadbandUSA", "BroadbandNow"]
            }
            
            nonprofit_params = {
                "category": "nonprofit",
                "search_terms": ["women-led", "women-owned", "nonprofit", "501c3"],
                "funding_type": ["grant"],
                "eligible_entities": ["nonprofits"],
                "sources": ["Grants.gov", "SBA", "IFundWomen", "Amber Grant Foundation"]
            }
            
            # Execute telecom search
            logging.info("Executing telecom grant search")
            telecom_grants = research_agent.search_grants(telecom_params)
            
            # Execute nonprofit search
            logging.info("Executing nonprofit grant search")
            nonprofit_grants = research_agent.search_grants(nonprofit_params)
            
            # Get priorities for ranking
            priorities = None  # Will be loaded from database in ranking
            
            # Rank grants
            logging.info("Ranking telecom grants")
            ranked_telecom = analysis_agent.rank_grants(telecom_grants, priorities)
            
            logging.info("Ranking nonprofit grants")
            ranked_nonprofit = analysis_agent.rank_grants(nonprofit_grants, priorities)
            
            # Get high-priority grants
            threshold = float(os.getenv("RELEVANCE_THRESHOLD", "85"))
            high_priority_telecom = [g for g in ranked_telecom if g.get("relevance_score", 0) >= threshold]
            high_priority_nonprofit = [g for g in ranked_nonprofit if g.get("relevance_score", 0) >= threshold]
            
            # Log search results
            logging.info(f"Found {len(telecom_grants)} telecom grants, {len(high_priority_telecom)} high priority")
            logging.info(f"Found {len(nonprofit_grants)} nonprofit grants, {len(high_priority_nonprofit)} high priority")
            
            # Send notifications for high-priority grants
            from utils.notification_manager import NotificationManager
            notifier = NotificationManager()
            
            if high_priority_telecom:
                logging.info(f"Sending notification for {len(high_priority_telecom)} high-priority telecom grants")
                notifier.send_grant_alert(high_priority_telecom)
                
            if high_priority_nonprofit:
                logging.info(f"Sending notification for {len(high_priority_nonprofit)} high-priority nonprofit grants")
                notifier.send_grant_alert(high_priority_nonprofit)
            
            return True
            
        except Exception as e:
            logging.error(f"Error executing scheduled search: {str(e)}")
            return False 