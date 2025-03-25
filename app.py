import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import plotly.express as px
import plotly.graph_objects as go

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

# Custom CSS for enhanced UI
st.markdown("""
<style>
    /* Card styling */
    .grant-card {
        background-color: #ffffff;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        border-left: 5px solid #2e6dd9;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .grant-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 8px rgba(0, 0, 0, 0.15);
    }
    
    /* Tag styling */
    .tag {
        display: inline-block;
        padding: 3px 8px;
        margin-right: 5px;
        border-radius: 15px;
        font-size: 12px;
        font-weight: 500;
    }
    .tag-telecom {
        background-color: #e6f3ff;
        color: #0366d6;
    }
    .tag-nonprofit {
        background-color: #f1e7fd;
        color: #6f42c1;
    }
    .tag-high {
        background-color: #fff3cd;
        color: #856404;
    }
    
    /* Responsive layout */
    @media (max-width: 768px) {
        .grant-card {
            padding: 15px;
        }
    }
    
    /* Header styling */
    .main-header {
        color: #2e6dd9;
        font-size: 2.2em;
        font-weight: 700;
        margin-bottom: 0.5em;
    }
    
    /* Search section styling */
    .search-box {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    
    /* Button styling */
    .stButton>button {
        border-radius: 20px;
        font-weight: 500;
        border: none;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #495057;
    }
    
    /* Metric styling */
    .metric-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        text-align: center;
    }
    
    /* Timeline styling */
    .timeline-item {
        display: flex;
        margin-bottom: 10px;
    }
    .timeline-date {
        width: 100px;
        font-weight: 500;
        color: #495057;
    }
    .timeline-content {
        flex-grow: 1;
        border-left: 2px solid #dee2e6;
        padding-left: 15px;
        padding-bottom: 10px;
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
        'categories': ['All'],
        'search_text': '',
        'sort_by': 'relevance_score'
    }
    
if 'search_results' not in st.session_state:
    st.session_state.search_results = []
    
if 'last_search' not in st.session_state:
    st.session_state.last_search = None

def get_metric_data():
    """Get real-time metric data from MongoDB."""
    try:
        high_priority_count = len(mongo_client.get_grants(min_score=85))
        
        # Calculate grants closing in next 7 days
        upcoming_deadline = len(mongo_client.get_grants(days_to_deadline=7))
        
        # Calculate total potential funding
        all_grants = mongo_client.get_grants(limit=500)
        total_funding = sum(grant.get('amount', 0) for grant in all_grants if isinstance(grant.get('amount'), (int, float)))
        
        # Get grants by category
        telecom_grants = len(mongo_client.get_grants(category="telecom"))
        nonprofit_grants = len(mongo_client.get_grants(category="nonprofit"))
        
        return {
            "high_priority": high_priority_count,
            "upcoming_deadline": upcoming_deadline,
            "total_funding": total_funding,
            "telecom_grants": telecom_grants,
            "nonprofit_grants": nonprofit_grants
        }
    except Exception as e:
        logger.error(f"Error fetching metric data: {str(e)}")
        return {
            "high_priority": 0,
            "upcoming_deadline": 0,
            "total_funding": 0,
            "telecom_grants": 0,
            "nonprofit_grants": 0
        }

def render_grant_card(grant):
    """Render an individual grant card with interactive elements."""
    grant_id = str(grant.get('_id', ''))
    title = grant.get('title', 'Untitled Grant')
    description = grant.get('description', 'No description available')
    source = grant.get('source_name', 'Unknown Source')
    
    # Format date
    deadline = grant.get('deadline')
    if isinstance(deadline, datetime):
        deadline_str = deadline.strftime('%B %d, %Y')
        days_remaining = calculate_days_remaining(deadline)
        deadline_display = f"{deadline_str} ({days_remaining} days remaining)"
    else:
        deadline_display = "No deadline specified"
    
    # Format amount
    amount = grant.get('amount')
    if isinstance(amount, (int, float)):
        amount_display = format_currency(amount)
    else:
        amount_display = "Amount not specified"
    
    # Category tag
    category = grant.get('category', 'other')
    if category == 'telecom':
        category_tag = '<span class="tag tag-telecom">Telecom</span>'
    elif category == 'nonprofit':
        category_tag = '<span class="tag tag-nonprofit">Nonprofit</span>'
    else:
        category_tag = f'<span class="tag">{category.capitalize()}</span>'
    
    # Relevance tag
    relevance = grant.get('relevance_score', 0)
    if relevance >= 85:
        relevance_tag = f'<span class="tag tag-high">{relevance:.1f}% Match</span>'
    else:
        relevance_tag = f'<span class="tag">{relevance:.1f}% Match</span>'
    
    # Truncate description
    short_desc = description[:200] + "..." if len(description) > 200 else description
    
    # Render card
    html = f"""
    <div class="grant-card" id="grant-{grant_id}">
        <h3>{title}</h3>
        <p>{category_tag} {relevance_tag}</p>
        <p><strong>Deadline:</strong> {deadline_display}</p>
        <p><strong>Amount:</strong> {amount_display}</p>
        <p><strong>Source:</strong> {source}</p>
        <p>{short_desc}</p>
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)
    
    # Action buttons
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("View Details", key=f"view_{grant_id}"):
            st.session_state.selected_grant = grant
            st.session_state.page = "Grant Details"
    
    with col2:
        if st.button("Save Grant", key=f"save_{grant_id}"):
            success = mongo_client.save_grant_for_user(grant_id)
            if success:
                st.success("Grant saved successfully!")
            else:
                st.error("Failed to save grant.")
    
    with col3:
        if st.button("Alert Me", key=f"alert_{grant_id}"):
            success = notifier.send_grant_alert([grant])
            if success:
                st.success("Alert sent!")
            else:
                st.error("Failed to send alert.")

def render_dashboard():
    """Render the dashboard page with metrics and high-priority grants."""
    st.markdown('<h1 class="main-header">📋 Grant Intelligence Dashboard</h1>', unsafe_allow_html=True)
    
    # Get metrics
    metrics = get_metric_data()
    
    # Display metric tiles
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <h2>{metrics['high_priority']}</h2>
                <p>High Priority Grants</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <h2>{metrics['upcoming_deadline']}</h2>
                <p>Closing This Week</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    with col3:
        st.markdown(
            f"""
            <div class="metric-card">
                <h2>${metrics['total_funding']:,.0f}</h2>
                <p>Available Funding</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    with col4:
        st.markdown(
            f"""
            <div class="metric-card">
                <h2>{metrics['telecom_grants'] + metrics['nonprofit_grants']}</h2>
                <p>Total Grants</p>
            </div>
            """, 
            unsafe_allow_html=True
        )
    
    # Live filters section
    with st.expander("🔍 Active Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.session_state.filters['min_score'] = st.slider(
                "Minimum Relevance Score", 
                min_value=0, 
                max_value=100, 
                value=st.session_state.filters['min_score'],
                step=5
            )
            
        with col2:
            st.session_state.filters['days_to_deadline'] = st.slider(
                "Days to Deadline", 
                min_value=7, 
                max_value=90, 
                value=st.session_state.filters['days_to_deadline'],
                step=7
            )
            
        with col3:
            st.session_state.filters['categories'] = st.multiselect(
                "Categories",
                options=['All', 'telecom', 'nonprofit', 'state'],
                default=st.session_state.filters['categories']
            )
    
    # High-priority grants section
    st.subheader("Priority Grant Opportunities")
    
    # Fetch grants based on filters
    category = None if 'All' in st.session_state.filters['categories'] else st.session_state.filters['categories']
    grants = mongo_client.get_grants(
        min_score=st.session_state.filters['min_score'],
        days_to_deadline=st.session_state.filters['days_to_deadline'],
        category=category,
        limit=10  # Limit to 10 grants for dashboard
    )
    
    if not grants:
        st.info("No grants match your current filter criteria. Try adjusting your filters.")
    else:
        for grant in grants:
            render_grant_card(grant)
    
    # Recent searches section
    st.subheader("Recent Search Activity")
    
    search_history = mongo_client.get_search_history(limit=5)
    if not search_history:
        st.info("No recent search activity.")
    else:
        for entry in search_history:
            search_date = entry.get('search_date', datetime.now()).strftime('%b %d, %H:%M')
            params = entry.get('parameters', {})
            category = params.get('category', 'general')
            results = entry.get('results_count', 0)
            
            st.markdown(
                f"""
                <div class="timeline-item">
                    <div class="timeline-date">{search_date}</div>
                    <div class="timeline-content">
                        <strong>{category.capitalize()} search</strong> yielded {results} results
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

def render_search():
    """Render the advanced search page."""
    st.markdown('<h1 class="main-header">🔎 Advanced Grant Search</h1>', unsafe_allow_html=True)
    
    # Search interface
    with st.form(key="search_form", clear_on_submit=False):
        st.markdown('<div class="search-box">', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Telecom Grant Filters")
            telecom_keywords = st.text_area(
                "Keywords (one per line)",
                value="broadband deployment\nrural connectivity\ntelecommunications\nfiber optic",
                height=100
            )
            
            funding_types = st.multiselect(
                "Funding Types",
                options=["Grant", "Cooperative Agreement", "Contract", "Loan"],
                default=["Grant", "Cooperative Agreement"]
            )
            
            geo_focus = st.text_input("Geographic Focus", value="LA-08")
        
        with col2:
            st.subheader("Nonprofit Grant Filters")
            nonprofit_keywords = st.text_area(
                "Keywords (one per line)",
                value="women-owned\nwomen-led\nnonprofit\nminority-owned",
                height=100
            )
            
            funding_range = st.slider(
                "Funding Range",
                min_value=5000,
                max_value=500000,
                value=(10000, 250000),
                step=5000,
                format="$%d"
            )
            
            eligibility = st.multiselect(
                "Eligibility",
                options=["501(c)(3)", "Small Business", "Women-Owned Business", "Minority-Owned Business"],
                default=["501(c)(3)", "Women-Owned Business"]
            )
        
        # Source selection
        st.subheader("Search Sources")
        
        source_cols = st.columns(4)
        
        with source_cols[0]:
            st.markdown("**Federal Sources**")
            grants_gov = st.checkbox("Grants.gov", value=True)
            sba_gov = st.checkbox("SBA.gov", value=True)
            usda = st.checkbox("USDA", value=True)
        
        with source_cols[1]:
            st.markdown("**Telecom Sources**")
            fcc = st.checkbox("FCC", value=True)
            ntia = st.checkbox("NTIA BroadbandUSA", value=True)
            rural_health = st.checkbox("Rural Health Info Hub", value=True)
        
        with source_cols[2]:
            st.markdown("**Women-Focused**")
            ifund_women = st.checkbox("IFundWomen", value=True)
            amber_grant = st.checkbox("Amber Grant Foundation", value=True)
            wfn = st.checkbox("Women Founders Network", value=True)
        
        with source_cols[3]:
            st.markdown("**State & Local**")
            louisiana = st.checkbox("Louisiana State", value=True)
            local_govt = st.checkbox("Local Government", value=True)
            private = st.checkbox("Private Foundations", value=True)
        
        # Advanced options
        with st.expander("Advanced Options"):
            search_method = st.radio(
                "Search Method",
                options=["Deep Search (Slower, More Comprehensive)", "Fast Search (Quicker Results)"],
                index=0
            )
            
            max_results = st.slider("Maximum Results", min_value=10, max_value=100, value=50)
            
            include_closed = st.checkbox("Include Closed Grants", value=False)
        
        # Search button
        search_button = st.form_submit_button("🚀 Launch Search", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        if search_button:
            # Process search parameters
            telecom_terms = [term.strip() for term in telecom_keywords.split("\n") if term.strip()]
            nonprofit_terms = [term.strip() for term in nonprofit_keywords.split("\n") if term.strip()]
            
            # Collect sources
            sources = []
            if grants_gov:
                sources.append("Grants.gov")
            if sba_gov:
                sources.append("SBA.gov")
            if usda:
                sources.append("USDA")
            if fcc:
                sources.append("FCC")
            if ntia:
                sources.append("NTIA BroadbandUSA")
            if rural_health:
                sources.append("Rural Health Info Hub")
            if ifund_women:
                sources.append("IFundWomen")
            if amber_grant:
                sources.append("Amber Grant Foundation")
            if wfn:
                sources.append("Women Founders Network")
            
            # Determine search category
            if telecom_terms and not nonprofit_terms:
                category = "telecom"
                search_terms = telecom_terms
            elif nonprofit_terms and not telecom_terms:
                category = "nonprofit"
                search_terms = nonprofit_terms
            else:
                category = "combined"
                search_terms = telecom_terms + nonprofit_terms
            
            # Create search parameters
            search_params = {
                "category": category,
                "search_terms": search_terms,
                "funding_type": funding_types,
                "sources": sources,
                "max_results": max_results,
                "include_closed": include_closed
            }
            
            # Add category-specific parameters
            if category in ["telecom", "combined"]:
                search_params["geo_restrictions"] = geo_focus
                
            if category in ["nonprofit", "combined"]:
                search_params["funding_range"] = funding_range
                search_params["eligibility"] = eligibility
            
            # Show search progress
            with st.spinner("Searching for grants..."):
                # In a real implementation, this would call the actual search
                # For demo, simulate results
                import time
                time.sleep(2)
                
                # Store search parameters and results
                st.session_state.last_search = search_params
                st.session_state.search_results = [
                    {
                        "_id": "mock1",
                        "title": "Rural Broadband Infrastructure Grant",
                        "description": "Funding for expanding broadband infrastructure in rural communities.",
                        "deadline": datetime.now() + timedelta(days=45),
                        "amount": 500000,
                        "category": "telecom",
                        "source_name": "USDA Rural Development",
                        "relevance_score": 92
                    },
                    {
                        "_id": "mock2",
                        "title": "Women's Business Center Grant",
                        "description": "Support for nonprofits that provide assistance to women entrepreneurs.",
                        "deadline": datetime.now() + timedelta(days=30),
                        "amount": 150000,
                        "category": "nonprofit",
                        "source_name": "SBA",
                        "relevance_score": 88
                    }
                ]
                
                # Log search to history
                search_history_entry = {
                    "search_date": datetime.now(),
                    "parameters": search_params,
                    "results_count": len(st.session_state.search_results),
                    "category": category
                }
                # mongo_client.store_search_history(**search_history_entry)
                
                st.success(f"Search complete! Found {len(st.session_state.search_results)} matching grants.")
    
    # Display search results if available
    if st.session_state.search_results:
        st.subheader("Search Results")
        
        # Sorting options
        sort_options = {
            "relevance_score": "Relevance Score (High to Low)",
            "deadline": "Application Deadline (Soonest First)",
            "amount": "Grant Amount (Highest First)"
        }
        
        sort_by = st.selectbox(
            "Sort By",
            options=list(sort_options.keys()),
            format_func=lambda x: sort_options[x],
            index=0
        )
        
        # Sort results
        if sort_by == "relevance_score":
            sorted_results = sorted(st.session_state.search_results, key=lambda x: x.get('relevance_score', 0), reverse=True)
        elif sort_by == "deadline":
            sorted_results = sorted(st.session_state.search_results, key=lambda x: x.get('deadline', datetime.max))
        elif sort_by == "amount":
            sorted_results = sorted(st.session_state.search_results, key=lambda x: x.get('amount', 0), reverse=True)
        else:
            sorted_results = st.session_state.search_results
        
        # Display results
        for grant in sorted_results:
            render_grant_card(grant)

def render_analytics():
    """Render the analytics dashboard."""
    st.markdown('<h1 class="main-header">📊 Grant Analytics Dashboard</h1>', unsafe_allow_html=True)
    
    # Get grant data for visualization
    grants = mongo_client.get_grants(limit=500)
    
    if not grants:
        st.info("No grant data available for analysis.")
        return
    
    # Create DataFrame
    grants_df = pd.DataFrame(grants)
    
    # Fix date columns
    for date_col in ['deadline', 'first_found_at']:
        if date_col in grants_df.columns:
            grants_df[date_col] = pd.to_datetime(grants_df[date_col])
    
    # Add calculated columns
    if 'deadline' in grants_df.columns:
        grants_df['days_to_deadline'] = (grants_df['deadline'] - datetime.now()).dt.days
    
    # Create tabs for different visualizations
    tab1, tab2, tab3 = st.tabs(["Distribution Analysis", "Timeline View", "Source Analysis"])
    
    with tab1:
        st.subheader("Grant Distribution by Category & Relevance")
        
        if 'category' in grants_df.columns and 'relevance_score' in grants_df.columns:
            # Category distribution chart
            category_counts = grants_df['category'].value_counts().reset_index()
            category_counts.columns = ['category', 'count']
            
            fig = px.pie(
                category_counts, 
                values='count', 
                names='category',
                title="Grant Distribution by Category",
                color_discrete_sequence=px.colors.qualitative.Set3,
                hole=0.4
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Relevance score distribution by category
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.box(
                    grants_df,
                    x='category',
                    y='relevance_score',
                    color='category',
                    title="Relevance Score Distribution by Category",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Calculate average relevance by category
                avg_relevance = grants_df.groupby('category')['relevance_score'].mean().reset_index()
                
                fig = px.bar(
                    avg_relevance,
                    x='category',
                    y='relevance_score',
                    title="Average Relevance Score by Category",
                    color='category',
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig.update_layout(yaxis_title="Average Relevance Score")
                
                st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Grant Deadlines Timeline")
        
        if 'deadline' in grants_df.columns:
            # Filter out grants with no deadline
            timeline_df = grants_df[grants_df['deadline'].notna()].copy()
            
            if not timeline_df.empty:
                # Sort by deadline
                timeline_df = timeline_df.sort_values('deadline')
                
                # Create timeline visualization
                fig = px.timeline(
                    timeline_df,
                    x_start='first_found_at',
                    x_end='deadline',
                    y='title',
                    color='category',
                    title="Grant Opportunity Timeline",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                
                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Grant Title",
                    yaxis_autorange="reversed"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Deadline distribution by month
                if len(timeline_df) > 0:
                    timeline_df['deadline_month'] = timeline_df['deadline'].dt.strftime('%B %Y')
                    deadline_counts = timeline_df['deadline_month'].value_counts().reset_index()
                    deadline_counts.columns = ['month', 'count']
                    deadline_counts = deadline_counts.sort_values('month')
                    
                    fig = px.bar(
                        deadline_counts,
                        x='month',
                        y='count',
                        title="Grant Deadlines by Month",
                        color_discrete_sequence=['#3366CC']
                    )
                    
                    fig.update_layout(
                        xaxis_title="Month",
                        yaxis_title="Number of Grants",
                        xaxis={'categoryorder':'category ascending'}
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No grants with deadline information available.")
        else:
            st.info("No deadline information available in the data.")
    
    with tab3:
        st.subheader("Grant Source Analysis")
        
        if 'source_name' in grants_df.columns:
            # Source distribution chart
            source_counts = grants_df['source_name'].value_counts().reset_index()
            source_counts.columns = ['source', 'count']
            
            fig = px.bar(
                source_counts.head(10),  # Top 10 sources
                x='count',
                y='source',
                title="Top 10 Grant Sources",
                orientation='h',
                color='count',
                color_continuous_scale=px.colors.sequential.Blues
            )
            
            fig.update_layout(
                xaxis_title="Number of Grants",
                yaxis_title="Source",
                yaxis={'categoryorder':'total ascending'}
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Source & Category Sunburst chart
            if 'category' in grants_df.columns:
                fig = px.sunburst(
                    grants_df,
                    path=['category', 'source_name'],
                    values='relevance_score',
                    title="Grant Sources by Category",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No source information available in the data.")

def render_settings():
    """Render the settings page."""
    st.markdown('<h1 class="main-header">⚙️ Settings</h1>', unsafe_allow_html=True)
    
    # Get current user settings
    current_settings = mongo_client.get_user_settings() or {}
    
    with st.form("settings_form"):
        # Notification Preferences
        st.subheader("Notification Preferences")
        
        col1, col2 = st.columns(2)
        
        with col1:
            notifications = {}
            notifications["sms_enabled"] = st.checkbox(
                "SMS Notifications",
                value=current_settings.get("notifications", {}).get("sms_enabled", True)
            )
            
            if notifications["sms_enabled"]:
                notifications["sms_number"] = st.text_input(
                    "Phone Number",
                    value=current_settings.get("notifications", {}).get("sms_number", "")
                )
        
        with col2:
            notifications["telegram_enabled"] = st.checkbox(
                "Telegram Notifications",
                value=current_settings.get("notifications", {}).get("telegram_enabled", True)
            )
            
            if notifications["telegram_enabled"]:
                notifications["telegram_username"] = st.text_input(
                    "Telegram Username",
                    value=current_settings.get("notifications", {}).get("telegram_username", "")
                )
        
        # Alert Thresholds
        st.subheader("Alert Thresholds")
        
        relevance_threshold = st.slider(
            "Minimum Relevance Score for Alerts",
            min_value=0,
            max_value=100,
            value=current_settings.get("relevance_threshold", 85),
            step=5
        )
        
        deadline_threshold = st.slider(
            "Days to Deadline Threshold",
            min_value=7,
            max_value=90,
            value=current_settings.get("deadline_threshold", 30),
            step=1
        )
        
        # Search Scheduling
        st.subheader("Search Scheduling")
        
        schedule_frequency = st.radio(
            "Search Frequency",
            options=["Twice Weekly", "Weekly", "Daily"],
            index=0 if current_settings.get("schedule_frequency") == "Twice Weekly" else 
                  1 if current_settings.get("schedule_frequency") == "Weekly" else
                  2 if current_settings.get("schedule_frequency") == "Daily" else 0
        )
        
        if schedule_frequency == "Twice Weekly":
            schedule_days = st.multiselect(
                "Search Days",
                options=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                default=current_settings.get("schedule_days", ["Monday", "Thursday"])
            )
        elif schedule_frequency == "Weekly":
            schedule_day = st.selectbox(
                "Search Day",
                options=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
                index=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].index(
                    current_settings.get("schedule_days", ["Monday"])[0]
                ) if current_settings.get("schedule_days") else 0
            )
            schedule_days = [schedule_day]
        else:
            schedule_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        
        schedule_time = st.time_input(
            "Search Time",
            value=datetime.strptime(
                current_settings.get("schedule_time", "10:00"), 
                "%H:%M"
            ).time() if isinstance(current_settings.get("schedule_time"), str) else datetime.strptime("10:00", "%H:%M").time()
        )
        
        # Apply settings
        if st.form_submit_button("Save Settings"):
            # Compile settings
            settings = {
                "notifications": notifications,
                "relevance_threshold": relevance_threshold,
                "deadline_threshold": deadline_threshold,
                "schedule_frequency": schedule_frequency,
                "schedule_days": schedule_days,
                "schedule_time": schedule_time.strftime("%H:%M"),
                "updated_at": datetime.now()
            }
            
            # Save to database
            success = mongo_client.save_user_settings(settings)
            
            if success:
                st.success("Settings saved successfully!")
            else:
                st.error("Failed to save settings. Please try again.")

def main():
    """Main application entry point."""
    # Sidebar navigation
    with st.sidebar:
        st.image("logo.png", width=200)  # Add a logo image if available
        
        st.title("Navigation")
        
        selected_page = st.radio(
            "Go to:",
            options=["Dashboard", "Search", "Analytics", "Settings"],
            index=["Dashboard", "Search", "Analytics", "Settings"].index(st.session_state.page) if st.session_state.page in ["Dashboard", "Search", "Analytics", "Settings"] else 0
        )
        
        st.session_state.page = selected_page
        
        # Last updated information
        st.markdown("---")
        st.caption(f"Last updated: {datetime.now().strftime('%b %d, %Y %H:%M')}")
        
        # App information
        with st.expander("About", expanded=False):
            st.markdown("""
            **Kevin's Smart Grant Finder**
            
            An AI-powered grant search system that automatically finds and ranks grant opportunities for telecommunications and women-owned nonprofit sectors.
            
            Version 1.0
            """)
    
    # Render selected page
    if st.session_state.page == "Dashboard":
        render_dashboard()
    elif st.session_state.page == "Search":
        render_search()
    elif st.session_state.page == "Analytics":
        render_analytics()
    elif st.session_state.page == "Settings":
        render_settings()
    elif st.session_state.page == "Grant Details" and "selected_grant" in st.session_state:
        # Grant details page
        grant = st.session_state.selected_grant
        st.title(grant.get("title", "Grant Details"))
        
        # Back button
        if st.button("← Back to Search"):
            st.session_state.page = "Search"
            st.experimental_rerun()
        
        # Display full grant details
        st.subheader("Grant Details")
        
        # Format full details
        st.markdown(f"**Deadline:** {grant.get('deadline').strftime('%B %d, %Y') if isinstance(grant.get('deadline'), datetime) else 'Not specified'}")
        st.markdown(f"**Amount:** {format_currency(grant.get('amount')) if isinstance(grant.get('amount'), (int, float)) else 'Not specified'}")
        st.markdown(f"**Source:** {grant.get('source_name', 'Unknown Source')}")
        st.markdown(f"**Category:** {grant.get('category', 'Not categorized')}")
        st.markdown(f"**Relevance Score:** {grant.get('relevance_score', 0):.1f}%")
        
        # Full description
        st.subheader("Description")
        st.write(grant.get("description", "No description available"))
        
        # Action buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Save Grant", key="save_detail"):
                success = mongo_client.save_grant_for_user(str(grant.get("_id", "")))
                if success:
                    st.success("Grant saved successfully!")
                else:
                    st.error("Failed to save grant.")
        
        with col2:
            if st.button("Send Notification", key="notify_detail"):
                success = notifier.send_grant_alert([grant])
                if success:
                    st.success("Notification sent!")
                else:
                    st.error("Failed to send notification.")

if __name__ == "__main__":
    main()