import streamlit as st
from typing import Dict, Optional
from datetime import datetime

def display_grant_field(label, value, formatter=None, suffix=None, is_link=False, markdown=False):
    """Display a field in the grant details view with consistent formatting."""
    if value:
        if formatter:
            value = formatter(value)
        if suffix:
            value = f"{value} {suffix}"
        
        if is_link:
            st.markdown(f"**{label}:** [{value}]({value})")
        elif markdown:
            st.markdown(f"**{label}:** {value}")
        else:
            st.markdown(f"**{label}:** {value}")
    else:
        st.markdown(f"**{label}:** N/A")

def render_grant_card(grant: Dict, current_page: str = "Dashboard") -> None:
    """Render a grant card with consistent styling across pages."""
    with st.container():
        st.markdown(f"""
        <div class="grant-card">
            <h3>{grant['title']}</h3>
            <p><strong>Amount:</strong> {grant.get('amount', 'Not specified')}</p>
            <p><strong>Deadline:</strong> {grant.get('deadline', 'No deadline specified')}</p>
            <p><strong>Score:</strong> {grant.get('relevance_score', 'N/A')}</p>
            <p>{grant.get('description', '')[:200]}...</p>
        </div>
        """, unsafe_allow_html=True)

def load_custom_css():
    """Load custom CSS styles used across pages."""
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
    </style>
    """, unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables used across pages."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
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