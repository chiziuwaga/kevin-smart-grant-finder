import os
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import secrets

import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go

# Add Telegram imports
import telegram
from telegram.ext import Application

# Page configuration must be the first Streamlit command
st.set_page_config(
    page_title="Kevin's Smart Grant Finder",
    page_icon="📋",
    layout="wide"
)

from database.mongodb_client import MongoDBClient
from database.pinecone_client import PineconeClient
from config.logging_config import setup_logging
from utils.helpers import display_grant_field
from utils.notification_manager import NotificationManager

# Initialize clients
try:
    mongo_client = MongoDBClient()
    pinecone_client = PineconeClient()
    notifier = NotificationManager()

    # Initialize Telegram Bot Application
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not telegram_token:
        logger.warning("TELEGRAM_BOT_TOKEN not found. Telegram features disabled.")
        telegram_app = None
    else:
        telegram_app = Application.builder().token(telegram_token).build()
        logger.info("Telegram Bot Application initialized.")

    logger.info("All clients initialized.")
except Exception as e:
    logger.critical(f"Failed to initialize core components: {str(e)}", exc_info=True)
    st.error("Fatal Error: Application failed to initialize. Please check logs and configuration.")
    st.stop()

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'dashboard'
if 'filters' not in st.session_state:
    st.session_state.filters = {}
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'selected_grant' not in st.session_state:
    st.session_state.selected_grant = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Add Telegram OTP state
if 'otp_code' not in st.session_state:
    st.session_state.otp_code = None
if 'otp_expiry' not in st.session_state:
    st.session_state.otp_expiry = None
if 'otp_sent' not in st.session_state:
    st.session_state.otp_sent = False

def generate_otp(length=6):
    """Generates a secure random OTP."""
    return "".join(secrets.choice("0123456789") for _ in range(length))

async def send_telegram_message(chat_id, message):
    """Helper to send message using the initialized Telegram app."""
    if not telegram_app:
        logger.error("Telegram app not initialized. Cannot send message.")
        return False
    try:
        await telegram_app.bot.send_message(chat_id=chat_id, text=message)
        logger.info(f"Message sent to Telegram chat ID {chat_id}")
        return True
    except telegram.error.TelegramError as e:
        logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred sending Telegram message: {e}")
        return False

async def send_telegram_otp():
    """Generates OTP, stores it, and sends it via Telegram."""
    admin_chat_id = os.getenv('ADMIN_TELEGRAM_CHAT_ID')
    if not admin_chat_id:
        st.error("Admin Telegram Chat ID not configured.")
        logger.error("ADMIN_TELEGRAM_CHAT_ID environment variable not set.")
        return False
    if not telegram_app:
        st.error("Telegram Bot not configured.")
        return False

    otp = generate_otp()
    expiry_time = time.time() + 300  # OTP valid for 5 minutes
    st.session_state.otp_code = otp
    st.session_state.otp_expiry = expiry_time

    message = f"Your Kevin's Smart Grant Finder login OTP is: {otp}\nIt is valid for 5 minutes."

    if await send_telegram_message(admin_chat_id, message):
        st.session_state.otp_sent = True
        logger.info(f"OTP sent to Admin Chat ID: {admin_chat_id}")
        return True
    else:
        st.error("Failed to send OTP via Telegram.")
        st.session_state.otp_code = None
        st.session_state.otp_expiry = None
        st.session_state.otp_sent = False
        return False

def check_telegram_otp(user_input_code):
    """Verifies the user-entered OTP against the stored one."""
    stored_otp = st.session_state.get('otp_code')
    expiry_time = st.session_state.get('otp_expiry')

    # Clear OTP from state regardless of outcome after check
    st.session_state.otp_code = None
    st.session_state.otp_expiry = None

    if not stored_otp or not expiry_time:
        st.error("OTP not found or session expired. Please request a new one.")
        logger.warning("OTP check failed: No OTP found in session state.")
        return False

    if time.time() > expiry_time:
        st.error("OTP has expired. Please request a new one.")
        logger.warning("OTP check failed: OTP expired.")
        return False

    if user_input_code == stored_otp:
        logger.info("OTP verification successful.")
        return True
    else:
        st.error("Invalid OTP entered.")
        logger.warning("OTP check failed: Invalid code entered.")
        return False

def login_screen():
    st.title("🔐 Admin Login")
    st.write("An OTP will be sent to the configured Admin Telegram account.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Send OTP to Admin Telegram"):
            import asyncio
            if asyncio.run(send_telegram_otp()):
                st.success("OTP sent successfully via Telegram!")

    with col2:
        if st.session_state.otp_sent:
            otp_code_input = st.text_input(
                "Enter OTP",
                type="password",
                key="otp_input"
            )

            if st.button("Verify OTP"):
                if check_telegram_otp(otp_code_input):
                    st.session_state.authenticated = True
                    st.session_state.otp_sent = False
                    st.success("Authentication successful!")
                    logger.info("Admin user authenticated successfully.")
                    time.sleep(1)
                    st.experimental_rerun()

def main_app():
    # Sidebar navigation
    with st.sidebar:
        st.title("Navigation")
        
        if st.button("📊 Dashboard"):
            st.session_state.page = 'dashboard'
            st.experimental_rerun()
        
        if st.button("🔍 Search"):
            st.session_state.page = 'search'
            st.experimental_rerun()
        
        if st.button("📎 Saved Grants"):
            st.session_state.page = 'saved_grants'
            st.experimental_rerun()
        
        if st.button("🔔 Alert History"):
            st.session_state.page = 'alert_history'
            st.experimental_rerun()
        
        st.markdown("---")
        
        if st.button("🚪 Logout"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.experimental_rerun()
    
    # Main content
    if st.session_state.page == 'dashboard':
        render_dashboard()
    elif st.session_state.page == 'search':
        render_search()
    elif st.session_state.page == 'grant_details':
        render_grant_details()
    elif st.session_state.page == 'saved_grants':
        render_saved_grants()
    elif st.session_state.page == 'alert_history':
        render_alert_history()

# Main app flow
if not st.session_state.authenticated:
    login_screen()
else:
    main_app()
