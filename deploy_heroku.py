import subprocess
import os
from dotenv import load_dotenv
import sys # To check Python version

# --- Configuration ---
HEROKU_APP_NAME = "smartgrantfinder" # <<< CORRECTED based on dashboard

# --- Load Environment Variables ---
print("Loading environment variables from .env file...")
load_dotenv()
print(".env file loaded.")

# --- Define Required Variables for Heroku ---
# These keys MUST match the keys in your .env file
# Pinecone vars are excluded as we're deferring the issue
# Heroku vars are excluded unless needed by heroku_manager.py
REQUIRED_ENV_VARS = {
    # --- API Keys ---
    "AGENTQL_API_KEY": os.getenv("AGENTQL_API_KEY"),
    "PERPLEXITY_API_KEY": os.getenv("PERPLEXITY_API_KEY"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    # --- Database ---
    "MONGODB_USER": os.getenv("MONGODB_USER"),
    "MONGODB_PASSWORD": os.getenv("MONGODB_PASSWORD"),
    "MONGODB_HOST": os.getenv("MONGODB_HOST"),
    "MONGODB_DBNAME": os.getenv("MONGODB_DBNAME", "SmartGrantfinder"), # Use default from .env if present
    "MONGODB_AUTHSOURCE": os.getenv("MONGODB_AUTHSOURCE", "admin"),
    "MONGODB_SSL": os.getenv("MONGODB_SSL", "true"),
    # --- Notifications ---
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
    "ADMIN_TELEGRAM_CHAT_ID": os.getenv("ADMIN_TELEGRAM_CHAT_ID"),
    "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID"), # Added this based on NotificationManager
    # --- Application Settings (Optional but good to sync) ---
    # "RELEVANCE_THRESHOLD": os.getenv("RELEVANCE_THRESHOLD"),
    # "DEADLINE_THRESHOLD": os.getenv("DEADLINE_THRESHOLD"),
    # --- Heroku Specific (Only if actively used by app code) ---
    # "HEROKU_API_KEY": os.getenv("HEROKU_API_KEY"), # Remove quotes in .env if using
    # "HEROKU_APP_NAME": os.getenv("HEROKU_APP_NAME"), # Remove quotes in .env if using
}

# --- Function to Set Config Vars ---
def set_heroku_config_vars(app_name, env_vars):
    """Sets environment variables on Heroku using Heroku CLI."""
    print(f"\nAttempting to set config vars for Heroku app: {app_name}")

    # Filter out any variables that don't have a value locally
    valid_vars = {k: v for k, v in env_vars.items() if v is not None}
    print(f"Found {len(valid_vars)} variables with values locally to set on Heroku.")

    print("\nDEBUG: Variables to be set:")
    for k, v in valid_vars.items():
        # Mask sensitive values partially for debug output
        masked_value = v
        if "KEY" in k or "TOKEN" in k or "PASSWORD" in k:
            if len(v) > 8:
                masked_value = v[:4] + "..." + v[-4:]
            else:
                 masked_value = "********"
        print(f"  {k}={masked_value}")
    print("------------------------")

    if not valid_vars:
        print("No valid environment variables found to set.")
        return False

    # Construct the command string with proper quoting for shell
    # Using single quotes around values is generally safer for complex strings
    vars_string = " ".join([f"{k}='{v}'" for k, v in valid_vars.items()])
    command = f"heroku config:set {vars_string} --app {app_name}"

    print("\nExecuting Heroku CLI command...")
    # For debugging, uncomment the next line:
    # print(f"DEBUG: Command = heroku config:set [VARIABLES...] --app {app_name}") # Hide sensitive values in debug output

    try:
        # Run the command
        # Explicitly use utf-8 encoding for output/errors
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True, encoding='utf-8')
        print("\n--- Heroku CLI Output ---")
        print(result.stdout if result.stdout else "(No stdout)")
        print("------------------------")
        print("\nSuccessfully set Heroku config vars.")
        return True
    except subprocess.CalledProcessError as e:
        print("\n--- Error executing Heroku CLI command ---")
        print(f"Return code: {e.returncode}")
        print("\n--- Stdout ---")
        print(e.stdout if e.stdout else "(No stdout)")
        print("\n--- Stderr ---")
        print(e.stderr if e.stderr else "(No stderr)")
        print("--------------------------------------------")
        print("\nError setting Heroku config vars.")
        # Add specific advice for the 'startsWith' error
        if e.stderr and "'startsWith' of undefined" in e.stderr:
             print("\nADVICE: The 'startsWith of undefined' error often indicates an internal Heroku CLI issue.")
             print("Try setting the variables manually via the Heroku Dashboard (Settings -> Config Vars).")
             print("Also ensure your Heroku CLI is updated (`heroku update`).")
        return False
    except FileNotFoundError:
        print("\nError: 'heroku' command not found.")
        print("Please ensure the Heroku CLI is installed and its 'bin' directory is in your system's PATH environment variable.")
        print("You may need to restart your terminal or computer after installation/PATH update.")
        return False
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        return False

# --- Main Execution Block ---
if __name__ == "__main__":
    print("--- Heroku Deployment Script ---")
    print(f"Python Version: {sys.version}")

    print("\nChecking required environment variables locally...")
    missing_vars = [k for k, v in REQUIRED_ENV_VARS.items() if v is None]

    if missing_vars:
        print("\nError: The following environment variables are missing in your local .env file:")
        for var in missing_vars:
            print(f"- {var}")
        print("\nPlease add them to your .env file before running this script.")
        # Optional: List the values found for debugging
        # print("\nVariables found:")
        # for k, v in REQUIRED_ENV_VARS.items():
        #     print(f"- {k}: {'Set' if v else 'Not Set'}")
    else:
        print("All required local environment variables seem to be present.")

        # Attempt to set the variables on Heroku
        if set_heroku_config_vars(HEROKU_APP_NAME, REQUIRED_ENV_VARS):
            print("\n------------------------")
            print("\nScript finished successfully.")
            print("Config vars should now be set on Heroku.")
            print("Deployment from GitHub should trigger automatically if code was pushed.")
            print(f"Monitor deployment progress with: heroku logs --tail --app {HEROKU_APP_NAME}")
        else:
            print("\n------------------------")
            print("\nScript finished with errors.")
            print("Failed to set Heroku config vars. Please check the error messages above.")

    print("\n--- Script Complete ---")
