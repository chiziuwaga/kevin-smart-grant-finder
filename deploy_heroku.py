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

# --- Required Variables ---
REQUIRED_ENV_VARS = {
    # API Keys
    "PERPLEXITY_API_KEY": os.getenv("PERPLEXITY_API_KEY"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
    "PINECONE_API_KEY": os.getenv("PINECONE_API_KEY"),
    
    # Database
    "DATABASE_URL": os.getenv("DATABASE_URL"),
    
    # Application Settings
    "ENVIRONMENT": os.getenv("ENVIRONMENT", "production"),
    "ALLOWED_ORIGINS": os.getenv("ALLOWED_ORIGINS", "https://grant-finder.vercel.app"),
    
    # Optional but recommended
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
    "ADMIN_TELEGRAM_CHAT_ID": os.getenv("ADMIN_TELEGRAM_CHAT_ID")
}

def validate_config():
    """Validate configuration values"""
    errors = []
    warnings = []
    
    # Check required variables
    for key in ["PERPLEXITY_API_KEY", "OPENAI_API_KEY", "PINECONE_API_KEY", "DATABASE_URL"]:
        if not REQUIRED_ENV_VARS.get(key):
            errors.append(f"Missing required environment variable: {key}")
    
    # Validate DATABASE_URL format
    db_url = REQUIRED_ENV_VARS.get("DATABASE_URL", "")
    if db_url and not db_url.startswith(("postgresql://", "postgres://")):
        errors.append("DATABASE_URL must be a valid PostgreSQL connection string")
    
    # Check optional but recommended variables
    if not REQUIRED_ENV_VARS.get("TELEGRAM_BOT_TOKEN"):
        warnings.append("TELEGRAM_BOT_TOKEN not set - notifications will be disabled")
    
    return errors, warnings

def set_heroku_config_vars(app_name: str, env_vars: dict) -> bool:
    """Sets environment variables on Heroku using Heroku CLI."""
    print(f"\nAttempting to set config vars for Heroku app: {app_name}")
    
    valid_vars = {k: v for k, v in env_vars.items() if v is not None}
    if not valid_vars:
        print("No valid environment variables found to set.")
        return False
    
    try:
        command_list = ["heroku", "config:set"]
        for k, v in valid_vars.items():
            masked_value = v
            if any(sensitive in k.lower() for sensitive in ["key", "token", "password", "secret"]):
                masked_value = v[:4] + "..." + v[-4:] if len(v) > 8 else "********"
            print(f"Setting {k}={masked_value}")
            command_list.append(f"{k}={v}")
        command_list.extend(["--app", app_name])
        
        result = subprocess.run(command_list, check=True, capture_output=True, text=True, encoding='utf-8')
        print("\nSuccessfully set Heroku config vars.")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"\nError setting Heroku config vars: {e}")
        print("\nError output:")
        print(e.stderr if e.stderr else "(No error output)")
        return False
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        return False

if __name__ == "__main__":
    print("\n=== Heroku Deployment Script ===")
    print(f"Python Version: {sys.version}")
    
    # Validate configuration
    errors, warnings = validate_config()
    
    if errors:
        print("\nConfiguration errors found:")
        for error in errors:
            print(f"❌ {error}")
        print("\nPlease fix these errors before proceeding.")
        sys.exit(1)
    
    if warnings:
        print("\nConfiguration warnings:")
        for warning in warnings:
            print(f"⚠️ {warning}")
    
    # Set config vars
    if set_heroku_config_vars(HEROKU_APP_NAME, REQUIRED_ENV_VARS):
        print("\n✅ Configuration variables set successfully")
        print(f"\nMonitor deployment: heroku logs --tail --app {HEROKU_APP_NAME}")
    else:
        print("\n❌ Failed to set configuration variables")
