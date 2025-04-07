import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from utils.components import render_grant_card, load_custom_css
from utils.helpers import format_currency, calculate_days_remaining

# Load custom CSS
load_custom_css()

def render_search_filters():
    """Render the search filters sidebar."""
    with st.sidebar:
        st.subheader("Search Filters")
        
        # Text search
        st.session_state.filters['search_text'] = st.text_input(
            "Search Text",
            value=st.session_state.filters.get('search_text', '')
        )
        
        # Minimum score filter
        st.session_state.filters['min_score'] = st.slider(
            "Minimum Score",
            min_value=0,
            max_value=100,
            value=st.session_state.filters.get('min_score', 85)
        )
        
        # Days to deadline filter
        st.session_state.filters['days_to_deadline'] = st.number_input(
            "Days until Deadline",
            min_value=1,
            max_value=365,
            value=st.session_state.filters.get('days_to_deadline', 30)
        )
        
        # Categories filter
        categories = ['All', 'Technology', 'Healthcare', 'Education', 'Environment']
        st.session_state.filters['categories'] = st.multiselect(
            "Categories",
            options=categories,
            default=st.session_state.filters.get('categories', ['All'])
        )
        
        # Sort options
        st.session_state.filters['sort_by'] = st.selectbox(
            "Sort By",
            options=['relevance_score', 'deadline', 'amount'],
            index=0
        )
        
        # Apply filters button
        if st.button("Apply Filters"):
            st.session_state.last_search = datetime.now()

def run_search(filters):
    """Execute the search with the given filters."""
    try:
        mongo_client = st.session_state.mongo_client
        
        # Build query
        query = {
            "deadline": {"$gt": datetime.now()},
            "relevance_score": {"$gte": filters['min_score']}
        }
        
        # Add text search if provided
        if filters['search_text']:
            query["$text"] = {"$search": filters['search_text']}
        
        # Add category filter if not 'All'
        if 'All' not in filters['categories']:
            query["categories"] = {"$in": filters['categories']}
        
        # Add deadline filter
        deadline_limit = datetime.now() + timedelta(days=filters['days_to_deadline'])
        query["deadline"]["$lt"] = deadline_limit
        
        # Sort options
        sort_field = filters['sort_by']
        sort_order = -1 if sort_field == 'relevance_score' else 1
        
        # Execute search
        results = list(mongo_client.find(
            "grants",
            query,
            sort=[(sort_field, sort_order)],
            limit=20
        ))
        
        return results
    except Exception as e:
        st.error(f"Error executing search: {str(e)}")
        return []

def main():
    st.title("Search Grants")
    
    # Render search filters
    render_search_filters()
    
    # Main content area
    if st.session_state.last_search:
        with st.spinner("Searching..."):
            results = run_search(st.session_state.filters)
            
        if results:
            st.success(f"Found {len(results)} matching grants")
            for grant in results:
                render_grant_card(grant, current_page="Search")
        else:
            st.info("No grants found matching your criteria.")
    else:
        st.info("Use the filters in the sidebar to search for grants.")

if __name__ == "__main__":
    main() 