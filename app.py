import os
import logging
import time # Needed for logout delay and OTP expiry
from datetime import datetime, timedelta, time
from typing import Dict, List, Optional
from pathlib import Path
import secrets # For OTP generation

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
    layout="wide",
    initial_sidebar_state="expanded"
)

from database.mongodb_client import MongoDBClient
from database.pinecone_client import PineconeClient
from config.logging_config import setup_logging
from utils.helpers import format_currency, calculate_days_remaining
from utils.notification_manager import NotificationManager
from utils.heroku_manager import update_heroku_schedule, generate_cron_expression

# Import Agents and new Clients
from utils.agentql_client import AgentQLClient
from utils.perplexity_client import PerplexityClient
from agents.research_agent import ResearchAgent
from agents.analysis_agent import GrantAnalysisAgent

# Set up logging
setup_logging()
logger = logging.getLogger("grant_finder")

# Load environment variables
load_dotenv()

# Initialize clients with proper error handling
try:
    mongo_client = MongoDBClient()
    pinecone_client = PineconeClient()
    agentql_client = AgentQLClient()
    perplexity_client = PerplexityClient()
    notifier = NotificationManager()

    # Initialize Telegram Bot Application
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not telegram_token:
        logger.warning("TELEGRAM_BOT_TOKEN not found. Telegram features disabled.")
        telegram_app = None
    else:
        telegram_app = Application.builder().token(telegram_token).build()
        logger.info("Telegram Bot Application initialized.")

    # Initialize Agents
    research_agent = ResearchAgent(agentql_client, perplexity_client, mongo_client)
    analysis_agent = GrantAnalysisAgent(pinecone_client, mongo_client)

    logger.info("All clients and agents initialized.")
except Exception as e:
    # Log the specific error during initialization
    logger.critical(f"CRITICAL: Failed to initialize core components: {str(e)}", exc_info=True)
    # Display a user-friendly error in Streamlit and stop execution
    st.error("Fatal Error: Application failed to initialize. Please check logs and configuration.")
    st.stop() # Stop Streamlit execution if core components fail

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

if 'selected_grant' not in st.session_state:
    st.session_state.selected_grant = None

if 'previous_page' not in st.session_state: # For Back button logic
    st.session_state.previous_page = "Dashboard"

if 'authenticated' not in st.session_state:
     st.session_state.authenticated = False

# Add Telegram OTP state
if 'otp_code' not in st.session_state:
    st.session_state.otp_code = None
if 'otp_expiry' not in st.session_state:
    st.session_state.otp_expiry = None
if 'otp_sent' not in st.session_state: # Keep this to manage UI flow
    st.session_state.otp_sent = False

def get_metric_data():
    """Get real-time metric data from MongoDB."""
    try:
        now = datetime.utcnow()
        today_start = datetime(now.year, now.month, now.day)
        one_week_ago = now - timedelta(days=7)

        # Count high-priority grants (score >= 85)
        high_priority_count = mongo_client.grants_collection.count_documents({
            "relevance_score": {"$gte": 85}
        })

        # Count grants closing within 7 days
        upcoming_deadline_count = mongo_client.grants_collection.count_documents({
            "deadline": {"$lte": now + timedelta(days=7), "$gte": now}
        })

        # Count grants found today
        new_today_count = mongo_client.grants_collection.count_documents({
            "first_found_at": {"$gte": today_start}
        })

        # Count high-priority grants found in the last week
        new_high_priority_last_week = mongo_client.grants_collection.count_documents({
            "relevance_score": {"$gte": 85},
            "first_found_at": {"$gte": one_week_ago}
        })

        # Calculate total potential funding (example - needs refinement based on amount format)
        # This uses an aggregation pipeline for better performance
        pipeline = [
            {"$match": {"amount": {"$type": "number"}}}, # Filter for numeric amounts
            {"$group": {"_id": None, "totalFunding": {"$sum": "$amount"}}}
        ]
        funding_result = list(mongo_client.grants_collection.aggregate(pipeline))
        total_funding = funding_result[0]["totalFunding"] if funding_result else 0
        
        # Get grants by category
        telecom_grants = mongo_client.grants_collection.count_documents({"category": "telecom"})
        nonprofit_grants = mongo_client.grants_collection.count_documents({"category": "nonprofit"})

        # Prepare delta values (example logic)
        # In a real app, you'd fetch the previous state or calculate based on timestamps
        high_priority_delta = new_high_priority_last_week # Example: delta is just new grants last week
        new_today_display = f"+{new_today_count} Today"
        
        return {
            "high_priority": high_priority_count,
            "high_priority_delta": high_priority_delta,
            "upcoming_deadline": upcoming_deadline_count,
            "total_funding": total_funding,
            "telecom_grants": telecom_grants,
            "nonprofit_grants": nonprofit_grants,
            "new_today_display": new_today_display
        }
    except Exception as e:
        logger.error(f"Error fetching metric data: {str(e)}")
        return {
            "high_priority": 0, "high_priority_delta": 0,
            "upcoming_deadline": 0, "total_funding": 0,
            "telecom_grants": 0, "nonprofit_grants": 0,
            "new_today_display": "+0 Today"
        }

def render_grant_card(grant, current_page="Dashboard"):
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
            st.session_state.previous_page = current_page # Store where user came from
            st.session_state.page = "Grant Details"
            st.experimental_rerun() # Rerun to navigate
    
    with col2:
        if st.button("Save Grant", key=f"save_{grant_id}"):
            success = mongo_client.save_grant_for_user("default_user", grant_id)
            if success:
                st.success("Grant saved!")
            else:
                st.error("Failed to save grant.")
    
    with col3:
        if st.button("Alert Me", key=f"alert_{grant_id}"):
            # Pass user_id if needed by notifier
            success = notifier.send_grant_alert([grant], user_id="default_user") 
            if success:
                st.success("Alert sent!")
                # Record that alert was sent
                mongo_client.record_alert_sent("default_user", grant_id)
            else:
                st.error("Failed to send alert.")

def render_dashboard():
    """Render the dashboard page with metrics and high-priority grants."""
    st.markdown('<h1 class="main-header">📋 Grant Intelligence Dashboard</h1>', unsafe_allow_html=True)
    
    # Get metrics (now includes delta values)
    metrics = get_metric_data()
    
    # Display metric tiles
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="High Priority Grants",
            value=metrics['high_priority'],
            delta=f"+{metrics['high_priority_delta']} This Week", # Display delta
            delta_color="normal" # or "inverse" or "off"
        )
    
    with col2:
        st.metric(
            label="Closing This Week",
            value=metrics['upcoming_deadline']
        )
    
    with col3:
         # Format currency properly
        formatted_funding = f"${metrics['total_funding']:,.0f}" if metrics['total_funding'] > 0 else "$0"
        st.metric(
            label="Available Funding",
            value=formatted_funding
            # Add delta for funding if tracked
        )
    
    with col4:
        st.metric(
            label="New Today",
            value=metrics['new_today_display'].split(' ')[0].replace('+', ''), # Extract count
            #delta=metrics['new_today_display'] # Or display delta text here
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
            # Pass current page context
            render_grant_card(grant, current_page="Dashboard")
    
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
        
        # Source selection - Dynamic
        st.subheader("Search Sources")
        
        # Fetch sources from DB
        all_sources = mongo_client.get_sources_by_domain() # Fetch all sources
        source_names = sorted([s['name'] for s in all_sources if 'name' in s])

        # Use columns for better layout
        num_columns = 4
        source_cols = st.columns(num_columns)
        selected_sources = {}

        # Distribute sources into columns and create checkboxes
        sources_per_col = (len(source_names) + num_columns - 1) // num_columns
        for i, source_name in enumerate(source_names):
            col_index = i // sources_per_col
            with source_cols[col_index]:
                # Use source name as key and label, default to True for now
                selected_sources[source_name] = st.checkbox(source_name, value=True, key=f"source_{source_name}")
        
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
            
            final_selected_sources = [name for name, is_selected in selected_sources.items() if is_selected]
            
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
            
            search_params = {
                "category": category,
                "search_terms": search_terms,
                "funding_type": funding_types,
                "sources": final_selected_sources,
                "max_results": max_results,
                "include_closed": include_closed
                # Add other parameters like geo_focus, funding_range, eligibility
            }
            if category in ["telecom", "combined"]:
                search_params["geo_restrictions"] = geo_focus
            if category in ["nonprofit", "combined"]:
                search_params["funding_range"] = funding_range
                search_params["eligibility"] = eligibility

            
            # Show search progress
            with st.spinner("Performing deep search across multiple sources..."):
                # Call the actual search logic using agents
                search_results = run_live_search(search_params)
                st.session_state.search_results = search_results
                st.session_state.last_search = search_params # Keep track of last search params

                # Log search to history (already handled in run_live_search)
                # Removed redundant history logging here

                # Check if search returned results or if an error occurred (indicated by empty list)
                if search_results is not None: # Check if function executed without throwing exception
                    st.success(f"Search complete! Found {len(search_results)} matching grants.")
                    # If results are empty, it means no grants found, not necessarily an error
                    if not search_results:
                        st.info("No grants were found matching your specific criteria.")
                # else: # Error message is handled within run_live_search now
                    # st.error("An error occurred during the search. Please check application logs.")
    
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
            # Pass current page context
            render_grant_card(grant, current_page="Search Grants")
    elif search_button and st.session_state.search_results == []: # Explicitly check for empty results after search
        # Optional: keep the info message if search was run but found nothing
        # st.info("No grants were found matching your specific criteria.")
        pass

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
    
    user_id = "default_user" # Assuming single user for now
    current_settings = mongo_client.get_user_settings(user_id)

    # Default values if settings are not found or incomplete
    notifications_settings = current_settings.get("notifications", {})
    default_schedule_freq = current_settings.get("schedule_frequency", "Twice Weekly")
    default_schedule_days = current_settings.get("schedule_days", ["Monday", "Thursday"])
    # Handle time - could be stored as string or time object
    default_schedule_time_str = current_settings.get("schedule_time", "10:00")
    try:
        default_schedule_time_obj = datetime.strptime(default_schedule_time_str, "%H:%M").time()
    except (ValueError, TypeError):
        logger.warning(f"Invalid stored time '{default_schedule_time_str}', defaulting to 10:00")
        default_schedule_time_obj = time(10, 0)
    
    with st.form("settings_form"):
        st.subheader("Notification Preferences")
        col1, col2 = st.columns(2)
        with col1:
            sms_enabled = st.checkbox("SMS Notifications", value=notifications_settings.get("sms_enabled", False))
            sms_number = st.text_input("Phone Number (for SMS)", value=notifications_settings.get("sms_number", ""), disabled=not sms_enabled)
        with col2:
            telegram_enabled = st.checkbox("Telegram Notifications", value=notifications_settings.get("telegram_enabled", False))
            telegram_username = st.text_input("Telegram Username/ID", value=notifications_settings.get("telegram_username", ""), disabled=not telegram_enabled)

        st.subheader("Grant Filtering Thresholds")
        relevance_threshold = st.slider("Minimum Relevance Score", 50, 100, current_settings.get("relevance_threshold", 85), 5)
        deadline_threshold = st.slider("Maximum Days to Deadline", 7, 180, current_settings.get("deadline_threshold", 30), 7)

        # --- Search Scheduling (Interactive) ---
        st.subheader("Search Scheduling")
        schedule_frequency_options = ["Daily", "Weekly", "Twice Weekly"]
        try:
             schedule_freq_index = schedule_frequency_options.index(default_schedule_freq)
        except ValueError:
             schedule_freq_index = 2 # Default to Twice Weekly if stored value is invalid
        
        schedule_frequency = st.radio(
            "Search Frequency",
            options=schedule_frequency_options,
            index=schedule_freq_index,
            horizontal=True
        )

        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        # Ensure default days are valid before passing to multiselect
        valid_default_days = [day for day in default_schedule_days if day in weekdays]

        if schedule_frequency == "Daily":
            # Display info, days selection not needed
            st.caption("Search will run every day at the specified time.")
            selected_schedule_days = weekdays # Internally, daily means all days for cron
        elif schedule_frequency == "Weekly":
             selected_schedule_days = [st.selectbox(
                "Search Day",
                 options=weekdays,
                 index=weekdays.index(valid_default_days[0]) if valid_default_days else 0 # Default to Monday if invalid/empty
             )]
        else: # Twice Weekly (or more if options expanded)
            selected_schedule_days = st.multiselect(
                "Search Days",
                options=weekdays,
                default=valid_default_days,
                help="Select the days the search should run."
            )

        schedule_time_obj = st.time_input(
            "Search Time (UTC)",
            value=default_schedule_time_obj,
            help="Select the time (in UTC) the search should run."
        )

        # Display the generated cron expression for user confirmation
        if schedule_frequency and selected_schedule_days and schedule_time_obj:
            display_cron = generate_cron_expression(schedule_frequency, selected_schedule_days, schedule_time_obj)
            if display_cron:
                st.write(f"**Equivalent Cron Schedule:** `{display_cron}`")
            else:
                st.warning("Could not generate a preview for the selected schedule.")

        # --- Save Button --- 
        submitted = st.form_submit_button("💾 Save All Settings & Update Schedule")
        if submitted:
            # 1. Compile all settings
            settings_to_save = {
                "user_id": user_id,
                "notifications": {
                    "sms_enabled": sms_enabled,
                    "sms_number": sms_number,
                    "telegram_enabled": telegram_enabled,
                    "telegram_username": telegram_username,
                },
                "relevance_threshold": relevance_threshold,
                "deadline_threshold": deadline_threshold,
                "schedule_frequency": schedule_frequency,
                "schedule_days": selected_schedule_days,
                "schedule_time": schedule_time_obj.strftime("%H:%M"), # Store time as string
            }

            # 2. Save settings to MongoDB
            mongo_save_success = mongo_client.save_user_settings(settings_to_save, user_id)

            if mongo_save_success:
                st.success("Settings saved to database successfully!")
                # Clear cache if needed
                st.cache_data.clear()

                # 3. Attempt to update Heroku schedule
                heroku_schedule_settings = {
                    "schedule_frequency": schedule_frequency,
                    "schedule_days": selected_schedule_days,
                    "schedule_time": schedule_time_obj # Pass the time object
                }
                # IMPORTANT: Verify this command matches your Heroku Scheduler job
                heroku_command = "python run_scrapers.py"
                logger.info(f"Calling update_heroku_schedule with settings: {heroku_schedule_settings} for command: {heroku_command}")
                heroku_update_success = update_heroku_schedule(heroku_schedule_settings, scheduler_command=heroku_command)

                if heroku_update_success:
                    st.success("Heroku schedule update simulated successfully! (Check logs for details)")
                else:
                    st.error("Failed to update Heroku schedule. Check application logs and Heroku configuration.")
            else:
                st.error("Failed to save settings to database. Please try again.")

def login_screen():
    st.title("🔐 Admin Login")
    st.write("An OTP will be sent to the configured Admin Telegram account.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Send OTP to Admin Telegram"):
            # Use asyncio.run because Streamlit runs in a sync context
            import asyncio
            if asyncio.run(send_telegram_otp()):
                 st.success("OTP sent successfully via Telegram!")
            # Error messages handled within send_telegram_otp

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
                    st.session_state.otp_sent = False # Reset OTP flow state
                    st.success("Authentication successful!")
                    logger.info("Admin user authenticated successfully.")
                    time.sleep(1) # Brief pause before rerun
                    st.experimental_rerun()
                else:
                    # Error messages handled within check_telegram_otp
                    pass # Keep otp_sent True to allow retry

def main_app():
    # --- Sidebar Navigation --- (This part runs only if authenticated)
    st.sidebar.title("Navigation")
    # Add new pages to options
    page_options = ["Dashboard", "Search Grants", "Saved Grants", "Analytics", "Alert History", "Settings"]
    
    current_page_index = page_options.index(st.session_state.get('page', 'Dashboard'))
    st.session_state.page = st.sidebar.radio(
        "Go to:", 
        page_options, 
        index=current_page_index
    )

    # --- Logout Button --- 
    st.sidebar.divider()
    if st.sidebar.button("Logout"):
        # Clear relevant session state
        st.session_state.authenticated = False
        st.session_state.page = "Dashboard" # Reset page state
        st.session_state.selected_grant = None
        st.session_state.otp_sent = False
        logger.info("User logged out.")
        st.experimental_rerun()
        
    # --- Page Rendering --- (Based on sidebar selection)
    if st.session_state.page == "Dashboard":
        render_dashboard()
    elif st.session_state.page == "Search Grants":
        render_search()
    elif st.session_state.page == "Saved Grants":
        render_saved_grants()
    elif st.session_state.page == "Analytics":
        render_analytics()
    elif st.session_state.page == "Alert History":
        render_alert_history()
    elif st.session_state.page == "Settings":
        render_settings()
    elif st.session_state.page == "Grant Details":
        render_grant_details()
    else:
        render_dashboard() # Default to dashboard

# === Main Execution Logic ===
# (Keep CSS, get_metric_data, render_grant_card, render_dashboard, render_search, render_analytics, render_settings etc. below)

# Custom CSS (Assuming it's already defined above)

# Session state initialization (Also assuming defined above)

# Helper functions (Assuming get_metric_data, render_grant_card etc. are defined)
# ...

# Page rendering functions (Assuming render_dashboard, etc. are defined)
# ...

# --- OTP Functions --- (Moved here for better organization, ensure imports are at the top)
# Twilio Client setup check
twilio_verify_sid = os.getenv("TWILIO_VERIFY_SERVICE_SID")
twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")

try:
    if twilio_account_sid and twilio_auth_token:
        twilio_otp_client = Client(twilio_account_sid, twilio_auth_token)
    else:
        twilio_otp_client = None
        logger.warning("Twilio Account SID/Auth Token not found for OTP client.")
except Exception as e:
    twilio_otp_client = None
    logger.error(f"Failed to initialize Twilio client for OTP: {e}")

def send_otp(phone_number: str) -> bool:
    """Sends OTP using Twilio Verify."""
    if not twilio_verify_sid:
        st.error("Twilio Verify Service SID is not configured.")
        logger.error("TWILIO_VERIFY_SERVICE_SID not set in environment variables.")
        return False
    if not twilio_otp_client:
         st.error("Twilio client not initialized. Cannot send OTP.")
         return False

    try:
        verification = twilio_otp_client.verify.v2.services(twilio_verify_sid) \
            .verifications \
            .create(to=phone_number, channel='sms')
        
        if verification.status == 'pending':
            logger.info(f"OTP sent successfully to {phone_number}. Status: {verification.status}")
            return True
        else:
            st.error(f"Failed to send OTP. Status: {verification.status}")
            logger.error(f"Failed to send OTP to {phone_number}. Status: {verification.status}")
            return False
            
    except TwilioRestException as e:
        st.error(f"Twilio Error: {e.msg}")
        logger.error(f"Twilio API error sending OTP to {phone_number}: {e}")
        return False
    except Exception as e:
        st.error("An unexpected error occurred while sending the OTP.")
        logger.error(f"Unexpected error sending OTP to {phone_number}: {e}", exc_info=True)
        return False

def check_otp(phone_number: str, otp_code: str) -> bool:
    """Checks OTP using Twilio Verify."""
    # Ensure the number trying to verify is the allowed number
    allowed_phone_number = os.getenv("NOTIFY_PHONE_NUMBER")
    if phone_number != allowed_phone_number:
         logger.warning(f"OTP check attempt for non-allowed number: {phone_number}")
         # Don't give specific feedback about *why* it failed, just that it's invalid
         return False 

    if not twilio_verify_sid:
        st.error("Twilio Verify Service SID is not configured.")
        logger.error("TWILIO_VERIFY_SERVICE_SID not set for OTP check.")
        return False
    if not twilio_otp_client:
         st.error("Twilio client not initialized. Cannot check OTP.")
         return False

    try:
        verification_check = twilio_otp_client.verify.v2.services(twilio_verify_sid) \
            .verification_checks \
            .create(to=phone_number, code=otp_code)
        
        if verification_check.status == 'approved':
            logger.info(f"OTP verification successful for {phone_number}.")
            return True
        else:
            logger.warning(f"OTP verification failed for {phone_number}. Status: {verification_check.status}")
            return False
            
    except TwilioRestException as e:
        # Log specific Twilio errors, but return generic failure to user
        logger.error(f"Twilio API error checking OTP for {phone_number}: {e}")
        if e.code == 20404: # Resource not found (e.g., code expired or invalid)
             st.error("Verification code is invalid or has expired.")
        else:
             st.error("Failed to verify code due to a server error.")
        return False
    except Exception as e:
        st.error("An unexpected error occurred during verification.")
        logger.error(f"Unexpected error checking OTP for {phone_number}: {e}", exc_info=True)
        return False

# --- Replace Placeholder Search with Agent Logic --- 
def run_live_search(search_params: Dict) -> List[Dict]:
    """Runs the actual grant search using Research and Analysis Agents."""
    logger.info(f"Executing live search with params: {search_params}")
    try:
        # 1. Use Research Agent to find grants from various sources
        # Ensure AgentQL agents are set up if needed (can be done on demand)
        # research_agent.setup_search_agents() # Or call this periodically / on startup
        found_grants = research_agent.search_grants(search_params)

        if not found_grants:
            logger.info("Research Agent found no grants matching the criteria.")
            return []

        # 2. Use Analysis Agent to rank and summarize the found grants
        analyzed_grants = analysis_agent.rank_and_summarize_grants(found_grants)

        # 3. Store the analyzed grants back into MongoDB (optional, ResearchAgent might do this)
        # This ensures the DB has the latest relevance scores and summaries.
        # Consider if ResearchAgent already stores the final processed list.
        # For now, assume we need to store/update after analysis.
        if analyzed_grants:
             logger.info(f"Storing/Updating {len(analyzed_grants)} analyzed grants in MongoDB.")
             # Need a method in MongoDBClient to handle updates with scores/summaries
             # mongo_client.update_analyzed_grants(analyzed_grants)
             # Or, store initially via ResearchAgent and just update scores/summaries here.
             mongo_client.store_grants(analyzed_grants) # Using existing store_grants which upserts

        logger.info(f"Live search completed. Returning {len(analyzed_grants)} analyzed grants.")
        return analyzed_grants

    except Exception as e:
        logger.error(f"Error during live grant search execution: {e}", exc_info=True)
        st.error(f"An error occurred during the search. Please check logs.")
        return [] # Return empty list on failure

# --- New Page Rendering Functions --- 
def render_grant_details():
    """Renders the detailed view for a selected grant."""
    st.markdown('<h1 class="main-header">Grant Details</h1>', unsafe_allow_html=True)
    
    grant = st.session_state.get('selected_grant')

    if not grant:
        st.error("No grant selected or details lost. Please go back and select a grant.")
        if st.button("Go to Dashboard"):
            st.session_state.page = "Dashboard"
            st.experimental_rerun()
        return

    # Display fields (use helper for potentially missing fields)
    display_grant_field("Title", grant.get('title'))
    display_grant_field("Description", grant.get('description'), markdown=True)
    display_grant_field("Amount", grant.get('amount'), formatter=format_currency)
    display_grant_field("Deadline", grant.get('deadline'))
    display_grant_field("Source", grant.get('source_name'))
    display_grant_field("Source URL", grant.get('source_url'), is_link=True)
    display_grant_field("Category", grant.get('category'))
    display_grant_field("Relevance Score", grant.get('relevance_score'), suffix="%")
    display_grant_field("First Found", grant.get('first_found_at'))
    display_grant_field("Last Updated", grant.get('last_updated'))
    # Add other fields as necessary

    st.divider()
    
    # Back button using stored previous page
    if st.button(f"< Back to {st.session_state.previous_page}"):
        st.session_state.page = st.session_state.previous_page
        st.session_state.selected_grant = None # Clear selected grant
        st.experimental_rerun()

def render_saved_grants():
    """Renders the list of grants saved by the user."""
    st.markdown('<h1 class="main-header">📚 Saved Grants</h1>', unsafe_allow_html=True)
    
    user_id = "default_user" # Assuming single user
    saved_grants = mongo_client.get_saved_grants_for_user(user_id)
    
    if not saved_grants:
        st.info("You haven't saved any grants yet. Click 'Save Grant' on a grant card to add it here.")
        return
        
    st.write(f"Displaying {len(saved_grants)} saved grants.")
    st.divider()
    
    for grant in saved_grants:
        grant_id = grant['_id']
        # Use columns for layout: Grant Card | Remove Button
        col1, col2 = st.columns([4, 1]) 
        with col1:
             render_grant_card(grant, current_page="Saved Grants") # Pass context
        with col2:
             st.write(" ") # Add some space
             st.write(" ")
             if st.button("❌ Remove", key=f"remove_{grant_id}"):
                  success = mongo_client.remove_saved_grant_for_user(user_id, grant_id)
                  if success:
                       st.success("Grant removed from saved list.")
                       time.sleep(0.5) # Short delay before rerun
                       st.experimental_rerun()
                  else:
                       st.error("Failed to remove grant.")
        st.divider()

def render_alert_history():
    """Renders the user's alert history."""
    st.markdown('<h1 class="main-header">🔔 Alert History</h1>', unsafe_allow_html=True)
    
    user_id = "default_user"
    alert_history = mongo_client.get_alert_history_for_user(user_id, limit=50) # Increase limit?
    
    if not alert_history:
        st.info("No alert history found.")
        return
        
    # Display as a table or formatted list
    history_data = []
    for entry in alert_history:
        sent_at = entry.get('alert_sent_at')
        sent_at_str = sent_at.strftime("%Y-%m-%d %H:%M:%S UTC") if isinstance(sent_at, datetime) else "N/A"
        title = entry.get('grant_title', 'Grant details unavailable')
        url = entry.get('grant_source_url')
        link = f"[Link]({url})" if url else "N/A"
        history_data.append({
            "Sent At": sent_at_str,
            "Grant Title": title,
            # "Link": link # Maybe too noisy for table?
        })
    
    st.dataframe(history_data, use_container_width=True)
    
    # Alternative: Markdown list
    # for entry in alert_history:
    #     sent_at_str = entry.get('alert_sent_at', datetime.now()).strftime("%Y-%m-%d %H:%M UTC")
    #     title = entry.get('grant_title', 'Grant details unavailable')
    #     url = entry.get('grant_source_url')
    #     link_md = f" ([Link]({url}))" if url else ""
    #     st.markdown(f"- **{sent_at_str}:** Alert sent for '{title}'{link_md}")

# --- Helper function (can be moved to utils/helpers.py) ---
def display_grant_field(label, value, formatter=None, suffix=None, is_link=False, markdown=False):
    """Helper to display a field only if it has a value."""
    if value is not None and value != '':
        display_value = value
        if formatter:
            try:
                display_value = formatter(value)
            except Exception as e:
                 logger.warning(f"Formatter error for {label}: {e}")
                 display_value = str(value) # Fallback to string
        
        if suffix:
            display_value = f"{display_value}{suffix}"

        if is_link:
            st.markdown(f"**{label}:** [{value}]({value})", unsafe_allow_html=True)
        elif markdown:
             st.markdown(f"**{label}:**")
             st.markdown(value, unsafe_allow_html=True) # Allow basic markdown
        else:
            st.write(f"**{label}:** {display_value}")

# --- Entry Point --- 
if __name__ == "__main__":
    # Check authentication status
    if not st.session_state.get("authenticated", False):
        login_screen()
    else:
        main_app()