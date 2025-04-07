import os
import logging
from datetime import datetime, timedelta
from pathlib import Path
import asyncio

import streamlit as st
from dotenv import load_dotenv
import telegram
from telegram.ext import Application

from database.mongodb_client import MongoDBClient
from database.pinecone_client import PineconeClient
from config.logging_config import setup_logging
from utils.notification_manager import NotificationManager
from utils.components import load_custom_css, initialize_session_state
from agents.research_agent import ResearchAgent
from agents.analysis_agent import GrantAnalysisAgent
from utils.agentql_client import AgentQLClient
from utils.perplexity_client import PerplexityClient

# Page configuration must be the first Streamlit command
st.set_page_config(
    page_title="Kevin's Smart Grant Finder",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Set up logging
setup_logging()
logger = logging.getLogger("grant_finder")

# Load environment variables
load_dotenv()

# Initialize session state
initialize_session_state()

# Load custom CSS
load_custom_css()

def initialize_services():
    """Lazy initialization of services"""
    if 'services_initialized' not in st.session_state:
        try:
            st.session_state.mongo_client = MongoDBClient()
            st.session_state.pinecone_client = PineconeClient()
            st.session_state.agentql_client = AgentQLClient()
            st.session_state.perplexity_client = PerplexityClient()
            st.session_state.notifier = NotificationManager()

            # Initialize Telegram Bot Application
            telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
            if telegram_token:
                st.session_state.telegram_app = Application.builder().token(telegram_token).build()
                logger.info("Telegram Bot Application initialized.")
            else:
                logger.warning("TELEGRAM_BOT_TOKEN not found. Telegram features disabled.")
                st.session_state.telegram_app = None

            # Initialize Agents
            st.session_state.research_agent = ResearchAgent(
                st.session_state.agentql_client,
                st.session_state.perplexity_client,
                st.session_state.mongo_client
            )
            st.session_state.analysis_agent = GrantAnalysisAgent(
                st.session_state.pinecone_client,
                st.session_state.mongo_client
            )

            st.session_state.services_initialized = True
            logger.info("All clients and agents initialized.")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize services: {str(e)}", exc_info=True)
            return False
    return True

def main():
    st.title("Welcome to Kevin's Smart Grant Finder")
    
    if not st.session_state.authenticated:
        st.warning("Please log in to access the full functionality.")
        st.info("For testing purposes, authentication is currently bypassed.")
        st.session_state.authenticated = True
    
    if st.session_state.authenticated:
        # Initialize services only when authenticated
        services_ok = initialize_services()
        
        if not services_ok:
            st.error("Failed to initialize some services. Some features may be limited.")
        else:
            st.success("You're logged in! Use the sidebar to navigate through different sections.")
            
            # Display quick stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Active Grants", "150+")
            with col2:
                st.metric("Success Rate", "85%")
            with col3:
                st.metric("Total Funding Available", "$2.5M+")
            
            st.markdown("""
            ### 🚀 Getting Started
            1. Use the **Dashboard** to view recommended grants
            2. Try the **Search** page for specific criteria
            3. Check **Analytics** for insights
            4. Configure your preferences in **Settings**
            """)

if __name__ == "__main__":
    main() 