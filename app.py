import os
import logging
from datetime import datetime, timedelta, time
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
from utils.heroku_manager import update_heroku_schedule, generate_cron_expression

# Set up logging
setup_logging()
logger = logging.getLogger("grant_finder")

# Load environment variables
load_dotenv()

# Initialize clients with proper error handling
try:
    # Force mock clients for development
    USE_MOCK = True  # Always use mock data for development
    mongo_client = MongoDBClient(use_mock=True)  # Force mock data
    pinecone_client = PineconeClient(use_mock=True)  # Force mock data
    grant_scraper = GrantScraper(use_mock=True)
    notifier = NotificationManager(use_mock=True)
    logger.info("All clients initialized with mock data")
except Exception as e:
    logger.error(f"Failed to initialize clients: {str(e)}")
    st.error("Failed to initialize application components. Please check your configuration.")
    raise e

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
            
            # Collect SELECTED sources from the dynamic checkboxes
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
            
            # Create search parameters
            search_params = {
                "category": category,
                "search_terms": search_terms,
                "funding_type": funding_types,
                "sources": final_selected_sources, # Use dynamically selected sources
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
                # Prepare settings specifically for Heroku function (needs time object)
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
                    # Error messages are now handled within update_heroku_schedule
                    st.error("Failed to update Heroku schedule. Check application logs and Heroku configuration.")
            else:
                st.error("Failed to save settings to database. Please try again.")

def main():
    """Main application entry point."""
    # Sidebar navigation
    with st.sidebar:
        logo_path = "assets/logo.png"
        if Path(logo_path).exists():
            st.image(logo_path, width=200)  # Add a logo image if available
        
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