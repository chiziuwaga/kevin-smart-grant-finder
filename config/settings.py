"""
Application settings and configuration.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database settings
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'grantfinder'),
    'user': os.getenv('DB_USER', 'user'),
    'password': os.getenv('DB_PASSWORD', '')
}

# API settings
GRANTS_API_KEY = os.getenv('GRANTS_API_KEY')

# Application settings
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', 'default-secret-key')
APP_ENV = os.getenv('APP_ENV', 'development')