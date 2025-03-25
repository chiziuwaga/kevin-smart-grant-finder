import schedule
import time
import logging
from datetime import datetime
import pytz
from typing import Callable, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Scheduler:
    def __init__(self):
        """Initialize the scheduler with configuration from environment variables."""
        self.timezone = pytz.timezone(os.getenv("TIMEZONE", "America/New_York"))
        self.schedule_days = os.getenv("SCHEDULE_DAYS", "monday,thursday").lower().split(",")
        self.schedule_time = os.getenv("SCHEDULE_TIME", "10:00")
        
        # Validate schedule days
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        self.schedule_days = [day.strip() for day in self.schedule_days if day.strip() in valid_days]
        
        if not self.schedule_days:
            self.schedule_days = ["monday", "thursday"]  # Default to Monday and Thursday
            logging.warning("No valid schedule days found. Defaulting to Monday and Thursday.")
    
    def _localize_time(self, time_str: str) -> datetime:
        """Convert time string to timezone-aware datetime."""
        try:
            time_obj = datetime.strptime(time_str, "%H:%M").time()
            now = datetime.now(self.timezone)
            return self.timezone.localize(datetime.combine(now.date(), time_obj))
        except ValueError:
            logging.error(f"Invalid time format: {time_str}. Using 10:00 AM.")
            return self.timezone.localize(datetime.strptime("10:00", "%H:%M"))
    
    def schedule_job(self, job: Callable, name: Optional[str] = None) -> None:
        """Schedule a job to run on specified days and time."""
        schedule_time = self._localize_time(self.schedule_time)
        time_str = schedule_time.strftime("%H:%M")
        
        for day in self.schedule_days:
            if day == "monday":
                schedule.every().monday.at(time_str).do(job)
            elif day == "tuesday":
                schedule.every().tuesday.at(time_str).do(job)
            elif day == "wednesday":
                schedule.every().wednesday.at(time_str).do(job)
            elif day == "thursday":
                schedule.every().thursday.at(time_str).do(job)
            elif day == "friday":
                schedule.every().friday.at(time_str).do(job)
            elif day == "saturday":
                schedule.every().saturday.at(time_str).do(job)
            elif day == "sunday":
                schedule.every().sunday.at(time_str).do(job)
        
        job_name = name or job.__name__
        logging.info(f"Scheduled {job_name} to run at {time_str} on {', '.join(self.schedule_days)}")
    
    def run(self) -> None:
        """Run the scheduler continuously."""
        logging.info("Starting scheduler...")
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logging.error(f"Error in scheduler: {str(e)}")
                time.sleep(300)  # Wait 5 minutes on error before retrying
    
    def run_once(self) -> None:
        """Run all pending jobs once and exit."""
        logging.info("Running scheduled jobs once...")
        schedule.run_pending()
    
    def clear(self) -> None:
        """Clear all scheduled jobs."""
        schedule.clear()
        logging.info("Cleared all scheduled jobs") 