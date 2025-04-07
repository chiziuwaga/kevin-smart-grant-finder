import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

from utils.components import load_custom_css
from utils.helpers import format_currency

# Load custom CSS
load_custom_css()

def get_analytics_data():
    """Fetch and prepare data for analytics visualizations."""
    try:
        mongo_client = st.session_state.mongo_client
        
        # Get all grants
        grants = list(mongo_client.find("grants", {}))
        df = pd.DataFrame(grants)
        
        if df.empty:
            return None
        
        # Ensure datetime format for deadline
        df['deadline'] = pd.to_datetime(df['deadline'])
        
        return df
    except Exception as e:
        st.error(f"Error fetching analytics data: {str(e)}")
        return None

def render_funding_distribution(df):
    """Render funding distribution chart."""
    fig = px.histogram(
        df,
        x="amount",
        title="Distribution of Grant Amounts",
        labels={"amount": "Grant Amount ($)", "count": "Number of Grants"},
        nbins=20
    )
    st.plotly_chart(fig, use_container_width=True)

def render_category_breakdown(df):
    """Render category breakdown chart."""
    if 'categories' in df.columns:
        # Explode categories array into separate rows
        categories_df = df.explode('categories')
        category_counts = categories_df['categories'].value_counts()
        
        fig = px.pie(
            values=category_counts.values,
            names=category_counts.index,
            title="Grant Categories Distribution"
        )
        st.plotly_chart(fig, use_container_width=True)

def render_timeline_analysis(df):
    """Render timeline analysis chart."""
    # Group by month
    df['month'] = df['deadline'].dt.to_period('M')
    monthly_counts = df.groupby('month').size()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly_counts.index.astype(str),
        y=monthly_counts.values,
        mode='lines+markers',
        name='Number of Grants'
    ))
    
    fig.update_layout(
        title="Grant Deadlines Timeline",
        xaxis_title="Month",
        yaxis_title="Number of Grants"
    )
    st.plotly_chart(fig, use_container_width=True)

def render_success_metrics(df):
    """Render success metrics."""
    total_funding = df['amount'].sum()
    avg_score = df['relevance_score'].mean()
    active_grants = df[df['deadline'] > datetime.now()].shape[0]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Available Funding", format_currency(total_funding))
    with col2:
        st.metric("Average Relevance Score", f"{avg_score:.1f}")
    with col3:
        st.metric("Active Grants", active_grants)

def main():
    st.title("Grant Analytics")
    
    df = get_analytics_data()
    
    if df is not None:
        # Render success metrics
        render_success_metrics(df)
        
        # Create tabs for different visualizations
        tab1, tab2, tab3 = st.tabs([
            "Funding Distribution",
            "Category Breakdown",
            "Timeline Analysis"
        ])
        
        with tab1:
            render_funding_distribution(df)
        
        with tab2:
            render_category_breakdown(df)
        
        with tab3:
            render_timeline_analysis(df)
            
        # Additional insights
        st.subheader("Key Insights")
        
        # Calculate and display insights
        avg_amount = df['amount'].mean()
        median_amount = df['amount'].median()
        most_common_category = df.explode('categories')['categories'].mode().iloc[0]
        
        st.markdown(f"""
        - Average grant amount: {format_currency(avg_amount)}
        - Median grant amount: {format_currency(median_amount)}
        - Most common category: {most_common_category}
        - Number of grants analyzed: {len(df)}
        """)
    else:
        st.info("No data available for analytics.")

if __name__ == "__main__":
    main() 