import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import plotly.express as px

# Page configuration must be the first Streamlit command
st.set_page_config(
    page_title="Kevin's Smart Grant Finder",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

from database.mongodb_client import MongoDBClient
from database.pinecone_client import PineconeClient
from scrapers.sources.louisiana_scraper import LouisianaGrantScraper
from config.logging_config import setup_logging
from utils.helpers import format_currency, calculate_days_remaining
from scrapers.grant_scraper import GrantScraper
from utils.notification_manager import NotificationManager

# Set up logging
setup_logging()
logger = logging.getLogger("grant_finder")

# Load environment variables
load_dotenv()

# Initialize clients with proper error handling
try:
    # Use mock clients for development
    USE_MOCK = True
    mongodb_client = MongoDBClient(use_mock=USE_MOCK)
    pinecone_client = PineconeClient(use_mock=USE_MOCK)
    logger.info("Database clients initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database clients: {str(e)}")
    st.error("Failed to connect to databases. Please check your configuration.")

# Initialize components
mongo_client = MongoDBClient()
grant_scraper = GrantScraper()
notifier = NotificationManager()

# Custom CSS for enhanced visuals based on ASCII design in the document
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 2rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid #E5E7EB;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2563eb;
        height: 100%;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 1rem;
        color: #666;
    }
    .grant-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #2563eb;
    }
    .grant-title {
        font-size: 1.25rem;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 0.5rem;
    }
    .grant-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .grant-meta-item {
        background-color: #f3f4f6;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.875rem;
    }
    .sidebar-filter-section {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .main {
        padding: 2rem;
    }
    .stButton button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if 'page' not in st.session_state:
    st.session_state.page = "Dashboard"
if 'filters' not in st.session_state:
    st.session_state.filters = {
        'min_score': 85,
        'days_to_deadline': 30,
        'category': 'All',
        'search_text': ''
    }

def load_grants(min_score: float = None, days_to_deadline: int = None,
               category: str = None) -> pd.DataFrame:
    """Load grants from MongoDB and convert to DataFrame."""
    try:
        grants = mongodb_client.get_grants(
            min_score=min_score,
            days_to_deadline=days_to_deadline,
            category=category
        )
        
        if not grants:
            logger.info("No grants found matching criteria")
            return pd.DataFrame()
        
        df = pd.DataFrame(grants)
        if not df.empty and 'deadline' in df.columns:
            df['days_remaining'] = df['deadline'].apply(calculate_days_remaining)
        return df
    except Exception as e:
        logger.error(f"Error loading grants: {str(e)}")
        st.error("Failed to load grants. Please try again later.")
        return pd.DataFrame()

def display_metrics(df: pd.DataFrame):
    """Display key metrics in the dashboard."""
    try:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(
                f"""<div class='metric-card'>
                    <div class='metric-value'>{len(df)}</div>
                    <div class='metric-label'>Active Grants</div>
                </div>""",
                unsafe_allow_html=True
            )
        
        with col2:
            high_priority = len(df[df['score'] >= 0.85]) if not df.empty and 'score' in df.columns else 0
            st.markdown(
                f"""<div class='metric-card'>
                    <div class='metric-value'>{high_priority}</div>
                    <div class='metric-label'>High Priority</div>
                </div>""",
                unsafe_allow_html=True
            )
        
        with col3:
            if not df.empty and 'amount' in df.columns:
                total_amount = df['amount'].sum() 
            else:
                total_amount = 600000  # Mock value for development
            st.markdown(
                f"""<div class='metric-card'>
                    <div class='metric-value'>{format_currency(total_amount)}</div>
                    <div class='metric-label'>Total Available</div>
                </div>""",
                unsafe_allow_html=True
            )
        
        with col4:
            closing_soon = len(df[df['days_remaining'] <= 7]) if not df.empty and 'days_remaining' in df.columns else 0
            st.markdown(
                f"""<div class='metric-card'>
                    <div class='metric-value'>{closing_soon}</div>
                    <div class='metric-label'>Closing Soon</div>
                </div>""",
                unsafe_allow_html=True
            )
    except Exception as e:
        logger.error(f"Error displaying metrics: {str(e)}")
        st.error("Failed to display metrics. Please try again later.")

def display_grant_table(df: pd.DataFrame):
    """Display interactive grant table."""
    try:
        if df.empty:
            st.warning("No grants found matching the current filters.")
            return
        
        # Format DataFrame for display
        display_df = df.copy()
        if 'score' in display_df.columns:
            display_df['relevance'] = display_df['score'].apply(lambda x: f"{x*100:.1f}%")
        if 'amount' in display_df.columns:
            display_df['amount'] = display_df['amount'].apply(format_currency)
        if 'deadline' in display_df.columns:
            display_df['deadline'] = display_df['deadline'].dt.strftime('%Y-%m-%d')
        
        # Select columns to display
        available_columns = display_df.columns.tolist()
        columns_to_display = []
        for col in ['title', 'amount', 'deadline', 'relevance', 'source', 'category']:
            if col in available_columns:
                columns_to_display.append(col)
        
        # Use enhanced card display instead of table
        for _, row in display_df.iterrows():
            with st.container():
                st.markdown(
                    f"""<div class='grant-card'>
                        <div class='grant-title'>{row.get('title', 'Untitled Grant')}</div>
                        <div class='grant-meta'>
                            <span class='grant-meta-item'>💰 {row.get('amount', 'N/A')}</span>
                            <span class='grant-meta-item'>📅 {row.get('deadline', 'No deadline')}</span>
                            <span class='grant-meta-item'>🔥 Relevance: {row.get('relevance', 'N/A')}</span>
                            <span class='grant-meta-item'>🏢 {row.get('source', 'Unknown source')}</span>
                        </div>
                        <p>{row.get('description', '')[:150]}...</p>
                    </div>""",
                    unsafe_allow_html=True
                )
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.button(f"📋 View Details", key=f"view_{row.get('_id', '_')}")
                with col2:
                    st.button(f"💾 Save Grant", key=f"save_{row.get('_id', '_')}")
    except Exception as e:
        logger.error(f"Error displaying grant table: {str(e)}")
        st.error("Failed to display grant table. Please try again later.")

def render_dashboard():
    """Render the main dashboard page."""
    st.title("📋 Grant Intelligence Dashboard")
    
    # Latest Updates
    st.markdown("""
    ### Latest Updates
    - 5 new grants found in Telecommunications
    - 3 new grants found in Women-Owned Nonprofits
    """)
    
    # Key Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        with st.container():
            st.markdown("""
            <div class="metric-card">
                <h3>High Priority Grants</h3>
                <h2>12</h2>
                <p>+2 since last week</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        with st.container():
            st.markdown("""
            <div class="metric-card">
                <h3>Approaching Deadlines</h3>
                <h2>5</h2>
                <p>Within next 7 days</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        with st.container():
            st.markdown("""
            <div class="metric-card">
                <h3>Total Available Funding</h3>
                <h2>$4.2M</h2>
                <p>12% increase</p>
            </div>
            """, unsafe_allow_html=True)
    
    # Grant List
    st.markdown("### Recent High-Priority Grants")
    grants = mongo_client.get_grants(
        min_score=st.session_state.filters['min_score'],
        days_to_deadline=st.session_state.filters['days_to_deadline']
    )
    
    for grant in grants:
        with st.container():
            st.markdown(f"""
            <div class="grant-card">
                <h3>{grant['title']}</h3>
                <p><b>Deadline:</b> {grant['deadline'].strftime('%B %d, %Y') if grant['deadline'] else 'Rolling'} | 
                   <b>Amount:</b> ${grant['amount']:,.2f} if grant['amount'] else 'Varies'}} | 
                   <b>Score:</b> {grant['relevance_score']}%</p>
                <p>{grant['description'][:200]}...</p>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save Grant", key=f"save_{grant['_id']}"):
                    mongo_client.save_grant_for_user(str(grant['_id']))
                    st.success("Grant saved!")
            with col2:
                if st.button("Send Alert", key=f"alert_{grant['_id']}"):
                    notifier.send_grant_alert(grant)
                    st.success("Alert sent!")

def render_search():
    """Render the grant search page."""
    st.title("🔎 Search Grants")
    
    # Search Form
    with st.form("search_form"):
        # Category Selection
        category = st.selectbox(
            "Category",
            ["All", "Telecommunications", "Women-Owned Nonprofit"]
        )
        
        # Keywords
        keywords = st.text_input("Keywords")
        
        # Filters
        col1, col2 = st.columns(2)
        with col1:
            funding_type = st.multiselect(
                "Funding Type",
                ["Grant", "Loan", "Technical Assistance"]
            )
        with col2:
            eligible_entities = st.multiselect(
                "Eligible Entities",
                ["Nonprofits", "Municipalities", "Small Businesses"]
            )
        
        # Search Button
        search = st.form_submit_button("Search Now")
        
        if search:
            st.session_state.filters.update({
                'category': category,
                'search_text': keywords
            })
    
    # Results
    if search:
        grants = mongo_client.get_grants(**st.session_state.filters)
        st.markdown(f"### Found {len(grants)} Matching Grants")
        
        for grant in grants:
            with st.expander(f"{grant['title']} - Score: {grant['relevance_score']}%"):
                st.markdown(f"""
                **Deadline:** {grant['deadline'].strftime('%B %d, %Y') if grant['deadline'] else 'Rolling'}  
                **Amount:** ${grant['amount']:,.2f} if grant['amount'] else 'Varies'}}  
                **Source:** {grant['source_name']}
                
                {grant['description']}
                """)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save Grant", key=f"save_search_{grant['_id']}"):
                        mongo_client.save_grant_for_user(str(grant['_id']))
                        st.success("Grant saved!")
                with col2:
                    if st.button("Send Alert", key=f"alert_search_{grant['_id']}"):
                        notifier.send_grant_alert(grant)
                        st.success("Alert sent!")

def render_analytics():
    """Render the grant analytics page."""
    st.title("📊 Grant Analytics")
    
    # Time-based metrics
    col1, col2 = st.columns(2)
    
    with col1:
        # Create sample data for demonstration
        dates = pd.date_range(start='2024-01-01', end='2024-03-25', freq='D')
        values = pd.Series(range(len(dates))) * 2 + 10
        df = pd.DataFrame({'Date': dates, 'Grants Found': values})
        
        fig = px.line(df, x='Date', y='Grants Found', title='Grants Found Over Time')
        st.plotly_chart(fig)
    
    with col2:
        # Create sample category distribution
        categories = ['Telecom', 'Nonprofit', 'Infrastructure', 'Education']
        values = [40, 25, 20, 15]
        df = pd.DataFrame({'Category': categories, 'Percentage': values})
        
        fig = px.pie(df, values='Percentage', names='Category', title='Grant Distribution by Category')
        st.plotly_chart(fig)

def render_settings():
    """Render the settings page."""
    st.title("⚙️ Settings")
    
    # Notification Settings
    st.markdown("### Notification Preferences")
    
    col1, col2 = st.columns(2)
    with col1:
        sms_enabled = st.checkbox("SMS Alerts", value=True)
        if sms_enabled:
            st.text_input("Phone Number", value="+1234567890")
    
    with col2:
        telegram_enabled = st.checkbox("Telegram Alerts", value=True)
        if telegram_enabled:
            st.text_input("Telegram Username", value="@username")
    
    # Search Schedule
    st.markdown("### Search Schedule")
    schedule_days = st.multiselect(
        "Search Days",
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        default=["Monday", "Thursday"]
    )
    
    schedule_time = st.time_input("Search Time", value=datetime.strptime("10:00", "%H:%M"))
    
    # Save Settings
    if st.button("Save Settings"):
        # TODO: Implement settings save
        st.success("Settings saved successfully!")

# Main content router
if st.session_state.page == "Dashboard":
    render_dashboard()
elif st.session_state.page == "Search Grants":
    render_search()
elif st.session_state.page == "Grant Analytics":
    render_analytics()
else:  # Settings
    render_settings()

# Create Streamlit app instance
app = main

if __name__ == "__main__":
    main()