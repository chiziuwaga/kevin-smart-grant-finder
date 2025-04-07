import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

from utils.components import render_grant_card, load_custom_css
from utils.helpers import format_currency, calculate_days_remaining

# Load custom CSS
load_custom_css()

def get_metric_data():
    """Get metric data for the dashboard."""
    try:
        mongo_client = st.session_state.mongo_client
        total_grants = mongo_client.count_documents("grants", {})
        active_grants = mongo_client.count_documents(
            "grants",
            {"deadline": {"$gt": datetime.now()}}
        )
        total_funding = mongo_client.aggregate("grants", [
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ])
        return {
            "total_grants": total_grants,
            "active_grants": active_grants,
            "total_funding": next(total_funding)["total"] if total_funding else 0
        }
    except Exception as e:
        st.error(f"Error fetching metrics: {str(e)}")
        return {"total_grants": 0, "active_grants": 0, "total_funding": 0}

def render_metrics(metrics):
    """Render metric cards on the dashboard."""
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Grants", metrics["total_grants"])
    with col2:
        st.metric("Active Grants", metrics["active_grants"])
    with col3:
        st.metric("Total Available Funding", format_currency(metrics["total_funding"]))

def render_timeline_chart(grants_df):
    """Render a timeline chart of grant deadlines."""
    if not grants_df.empty:
        fig = px.timeline(
            grants_df,
            x_start="deadline",
            y="title",
            title="Grant Deadlines Timeline"
        )
        st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("Grant Dashboard")
    
    # Get metric data
    metrics = get_metric_data()
    render_metrics(metrics)
    
    # Get recommended grants
    try:
        mongo_client = st.session_state.mongo_client
        grants = list(mongo_client.find(
            "grants",
            {
                "deadline": {"$gt": datetime.now()},
                "relevance_score": {"$gt": 80}
            },
            limit=5
        ))
        
        if grants:
            st.subheader("Recommended Grants")
            for grant in grants:
                render_grant_card(grant)
            
            # Create timeline chart
            grants_df = pd.DataFrame(grants)
            render_timeline_chart(grants_df)
        else:
            st.info("No recommended grants found at this time.")
            
    except Exception as e:
        st.error(f"Error loading recommended grants: {str(e)}")

if __name__ == "__main__":
    main() 