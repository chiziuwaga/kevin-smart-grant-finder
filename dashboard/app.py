import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List

from database.mongodb_client import MongoDBClient
from database.pinecone_client import PineconeClient
from utils.scrapers.louisiana_scraper import LouisianaGrantScraper

# Initialize clients
mongodb_client = MongoDBClient()
pinecone_client = PineconeClient()

# Page configuration
st.set_page_config(
    page_title="Kevin's Smart Grant Finder",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
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
</style>
""", unsafe_allow_html=True)

def format_currency(amount: float) -> str:
    """Format amount as currency string."""
    return f"${amount:,.2f}"

def calculate_days_remaining(deadline: datetime) -> int:
    """Calculate days remaining until deadline."""
    if not deadline:
        return None
    return (deadline - datetime.now()).days

def load_grants(min_score: float = None, days_to_deadline: int = None,
               category: str = None) -> pd.DataFrame:
    """Load grants from MongoDB and convert to DataFrame."""
    grants = mongodb_client.get_grants(
        min_score=min_score,
        days_to_deadline=days_to_deadline,
        category=category
    )
    
    if not grants:
        return pd.DataFrame()
    
    df = pd.DataFrame(grants)
    if not df.empty and 'deadline' in df.columns:
        df['days_remaining'] = df['deadline'].apply(calculate_days_remaining)
    return df

def display_metrics(df: pd.DataFrame):
    """Display key metrics in the dashboard."""
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
        high_priority = len(df[df['score'] >= 0.85]) if not df.empty else 0
        st.markdown(
            f"""<div class='metric-card'>
                <div class='metric-value'>{high_priority}</div>
                <div class='metric-label'>High Priority</div>
            </div>""",
            unsafe_allow_html=True
        )
    
    with col3:
        total_amount = df['amount'].sum() if not df.empty and 'amount' in df else 0
        st.markdown(
            f"""<div class='metric-card'>
                <div class='metric-value'>{format_currency(total_amount)}</div>
                <div class='metric-label'>Total Available</div>
            </div>""",
            unsafe_allow_html=True
        )
    
    with col4:
        closing_soon = len(df[df['days_remaining'] <= 7]) if not df.empty else 0
        st.markdown(
            f"""<div class='metric-card'>
                <div class='metric-value'>{closing_soon}</div>
                <div class='metric-label'>Closing Soon</div>
            </div>""",
            unsafe_allow_html=True
        )

def display_grant_table(df: pd.DataFrame):
    """Display interactive grant table."""
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
    columns_to_display = [
        'title', 'amount', 'deadline', 'relevance',
        'source', 'category'
    ]
    
    st.dataframe(
        display_df[columns_to_display],
        use_container_width=True,
        hide_index=True
    )

def main():
    """Main dashboard application."""
    st.markdown("<h1 class='main-header'>📋 Kevin's Smart Grant Finder</h1>",
                unsafe_allow_html=True)
    
    # Sidebar filters
    st.sidebar.title("Filters")
    
    min_score = st.sidebar.slider(
        "Minimum Relevance Score",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.05,
        format="%d%%"
    )
    
    days_to_deadline = st.sidebar.slider(
        "Days to Deadline",
        min_value=1,
        max_value=90,
        value=30
    )
    
    categories = ["All", "federal", "state", "nonprofit"]
    selected_category = st.sidebar.selectbox(
        "Category",
        categories
    )
    
    # Load and filter data
    category = None if selected_category == "All" else selected_category
    grants_df = load_grants(
        min_score=min_score,
        days_to_deadline=days_to_deadline,
        category=category
    )
    
    # Display metrics
    display_metrics(grants_df)
    
    # Tabs for different views
    tab1, tab2 = st.tabs(["📋 Grants List", "📊 Analytics"])
    
    with tab1:
        st.subheader("Available Grants")
        display_grant_table(grants_df)
    
    with tab2:
        st.subheader("Grant Analytics")
        
        # Category distribution
        if not grants_df.empty and 'category' in grants_df.columns:
            st.write("Distribution by Category")
            category_counts = grants_df['category'].value_counts()
            st.bar_chart(category_counts)
        
        # Score distribution
        if not grants_df.empty and 'score' in grants_df.columns:
            st.write("Score Distribution")
            score_hist = pd.DataFrame({
                'score': grants_df['score']
            })
            st.bar_chart(score_hist)

if __name__ == "__main__":
    main()