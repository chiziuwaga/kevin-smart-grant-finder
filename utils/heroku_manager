# utils/heroku_manager.py
import os
import logging
import heroku3
from dotenv import load_dotenv
from typing import List, Optional

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# --- Cron Expression Generation ---

def _get_cron_day_of_week(days: List[str]) -> str:
    """Converts list of weekdays to cron format (0=Sun, 6=Sat)."""
    day_map = {
        "Sunday": 0, "Monday": 1, "Tuesday": 2, "Wednesday": 3,
        "Thursday": 4, "Friday": 5, "Saturday": 6
    }
    cron_days = [str(day_map[day]) for day in days if day in day_map]
    return ",".join(cron_days) if cron_days else '*' # Default to '*' if empty/invalid

def generate_cron_expression(frequency: str, days: List[str], time_str: str) -> Optional[str]:
    """
    Generates a cron expression based on user settings.

    Args:
        frequency: 'Daily', 'Weekly', 'Twice Weekly'.
        days: List of weekdays (e.g., ['Monday', 'Thursday']).
        time_str: Time in HH:MM format (e.g., '10:00').

    Returns:
        A cron expression string (e.g., '0 10 * * 1,4') or None if invalid.
    """
    try:
        if not time_str or ':' not in time_str:
             raise ValueError("Invalid time format: Expected HH:MM")
        hour, minute = map(int, time_str.split(':'))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError("Invalid time values")

        cron_minute = str(minute)
        cron_hour = str(hour)
        cron_day_of_month = '*'
        cron_month = '*'
        cron_day_of_week = '*'

        if frequency == 'Daily':
            # Runs every day at the specified time
            cron_day_of_week = '*'
        elif frequency in ['Weekly', 'Twice Weekly']:
            if not days:
                 logger.warning(f"No days specified for frequency '{frequency}'. Defaulting to daily schedule pattern.")
                 cron_day_of_week = '*' # Fallback to daily if no days provided for weekly/bi-weekly
            else:
                cron_day_of_week = _get_cron_day_of_week(days)
                if cron_day_of_week == '*':
                    logger.warning(f"Could not determine valid days for frequency '{frequency}' with days {days}. Defaulting to daily schedule pattern.")
                    # Fallback if days were invalid
                    cron_day_of_week = '*'

        # Format: minute hour day_of_month month day_of_week
        return f"{cron_minute} {cron_hour} {cron_day_of_month} {cron_month} {cron_day_of_week}"

    except Exception as e:
        logger.error(f"Error generating cron expression for {frequency}, {days}, {time_str}: {e}")
        return None

# --- Heroku Interaction ---

def update_heroku_schedule(schedule_settings: dict, scheduler_command: str = "python run_scrapers.py") -> bool:
    """
    Updates a specific Heroku Scheduler job based on provided settings.
    **Note:** Currently simulates the update due to complexity with heroku3 library.

    Args:
        schedule_settings: Dictionary containing 'schedule_frequency', 'schedule_days', 'schedule_time'.
        scheduler_command: The exact command the target Heroku Scheduler job runs.
                           **IMPORTANT: This must match your job command exactly.**

    Returns:
        True if the update was successful or simulated successfully, False otherwise.
    """
    heroku_api_key = os.getenv("HEROKU_API_KEY")
    heroku_app_name = os.getenv("HEROKU_APP_NAME")

    if not heroku_api_key or heroku_api_key == "YOUR_HEROKU_API_KEY_HERE":
        logger.error("Heroku API Key not configured in .env file.")
        # In a real app, might display a message to the user in Streamlit
        st.error("Heroku integration is not configured. Please set HEROKU_API_KEY in the environment.")
        return False
    if not heroku_app_name or heroku_app_name == "YOUR_HEROKU_APP_NAME_HERE":
        logger.error("Heroku App Name not configured in .env file.")
        st.error("Heroku integration is not configured. Please set HEROKU_APP_NAME in the environment.")
        return False

    # Generate the target cron expression
    frequency = schedule_settings.get('schedule_frequency')
    days = schedule_settings.get('schedule_days', [])
    time_str = schedule_settings.get('schedule_time') # Should be HH:MM

    if not frequency or not time_str:
        logger.warning("Incomplete schedule settings provided ({frequency}, {days}, {time_str}), cannot update Heroku schedule.")
        st.warning("Cannot update schedule: Frequency or Time is missing.")
        return False # Need all parts to form a valid schedule

    target_cron = generate_cron_expression(frequency, days, time_str)
    if not target_cron:
        logger.error("Failed to generate valid cron expression from settings.")
        st.error("Could not generate a valid schedule from the provided settings.")
        return False

    logger.info(f"Attempting to update Heroku schedule for '{heroku_app_name}' to '{target_cron}' for command '{scheduler_command}'")

    try:
        # Connect to Heroku
        heroku_conn = heroku3.from_key(heroku_api_key)
        app = heroku_conn.app(heroku_app_name)

        # Get existing scheduled jobs (Heroku Scheduler add-on)
        scheduler_jobs = app.scheduler_jobs()

        target_job = None
        for job in scheduler_jobs:
            # Ensure comparison is robust (strip whitespace, case-insensitive if needed)
            if job.command.strip() == scheduler_command.strip():
                target_job = job
                break

        if not target_job:
            logger.error(f"Could not find Heroku Scheduler job with command: '{scheduler_command}'. Please ensure the command matches exactly in your Heroku Scheduler settings.")
            st.error(f"Could not find the scheduled job running '{scheduler_command}'. Please check your Heroku Scheduler configuration.")
            return False

        # Check if update is needed
        # Heroku Scheduler might add frequency info (e.g., "~ H H * * *"),
        # so comparing directly with pure cron might fail. Need robust check or API update.
        # For now, we simplify the check assuming format consistency.
        current_schedule_parts = target_job.schedule.split()
        target_cron_parts = target_cron.split()
        
        # Basic check - might need refinement based on actual Heroku schedule formats
        if current_schedule_parts[:5] == target_cron_parts:
             logger.info(f"Heroku schedule for '{scheduler_command}' is already effectively '{target_cron}'. No update needed.")
             # We can return True here, but showing success message in UI might be better
             # return True 
             pass # Let it proceed to show success message after "simulation"
        
        # --- Placeholder for Actual Heroku API Update ---
        # See previous comment block for details on why this is a placeholder.
        logger.info(f"[SIMULATED] Would update Heroku job '{target_job.id}' schedule from '{target_job.schedule}' to '{target_cron}'")
        # Simulate success for now
        simulated_success = True
        # -----------------------------------------------

        if simulated_success:
            logger.info(f"Successfully simulated update of Heroku schedule for '{scheduler_command}' to '{target_cron}'")
            # User feedback will be handled in app.py
            return True
        else:
             logger.error(f"Failed to simulate update of Heroku schedule.")
             st.error("Failed to update the schedule on Heroku (simulation failed).")
             return False

    except heroku3.exceptions.NotFound as e:
         logger.error(f"Heroku app '{heroku_app_name}' not found: {e}")
         st.error(f"Heroku application '{heroku_app_name}' was not found. Check your .env settings.")
         return False
    except Exception as e:
        # Catch potential issues like addon not enabled, API errors, auth issues etc.
        logger.error(f"An unexpected error occurred while updating Heroku schedule: {e}", exc_info=True)
        st.error(f"An error occurred while communicating with Heroku: {e}")
        return False

if __name__ == '__main__':
    # Example Usage (for testing)
    import streamlit as st # Add temporarily for st.error/warning testing
    print("Testing cron generation:")
    print(f"Daily at 9:30 -> {generate_cron_expression('Daily', [], '09:30')}")
    print(f"Weekly Mon 14:00 -> {generate_cron_expression('Weekly', ['Monday'], '14:00')}")
    print(f"Twice Weekly Mon,Thu 8:15 -> {generate_cron_expression('Twice Weekly', ['Monday', 'Thursday'], '08:15')}")
    print(f"Twice Weekly No Days 8:15 -> {generate_cron_expression('Twice Weekly', [], '08:15')}") # Should default
    print(f"Invalid time -> {generate_cron_expression('Daily', [], '25:00')}")
    print(f"Invalid day -> {generate_cron_expression('Weekly', ['Funday'], '10:00')}")
    print(f"Missing time -> {generate_cron_expression('Daily', [], None)}")


    # # Example Heroku update call (won't run without real creds & job)
    # test_settings = {
    #     'schedule_frequency': 'Daily',
    #     'schedule_days': [], # Ignored for Daily
    #     'schedule_time': '11:00'
    # }
    # print("\nTesting Heroku update function (will likely fail without config):")
    # update_heroku_schedule(test_settings)
