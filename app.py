import streamlit as st
import time
from datetime import datetime, timedelta
from database.mongodb_client import MongoDBClient
from utils.helpers import display_grant_field
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Page config
st.set_page_config(
    page_title="Kevin's Smart Grant Finder",
    page_icon="🎯",
    layout="wide"
)

# Initialize clients
mongo_client = MongoDBClient()
twilio_client = Client(
    os.getenv('TWILIO_ACCOUNT_SID'),
    os.getenv('TWILIO_AUTH_TOKEN')
)

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
if 'phone_verified' not in st.session_state:
    st.session_state.phone_verified = False

def send_otp(phone_number):
    try:
        if not os.getenv('TWILIO_VERIFY_SID'):
            st.error('Twilio Verify SID not configured')
            return False
            
        verification = twilio_client.verify.v2.services(
            os.getenv('TWILIO_VERIFY_SID')
        ).verifications.create(to=phone_number, channel='sms')
        
        return verification.status == 'pending'
    except TwilioRestException as e:
        st.error(f'Failed to send OTP: {str(e)}')
        return False

def check_otp(phone_number, code):
    try:
        if phone_number != os.getenv('NOTIFY_PHONE_NUMBER'):
            st.error('Unauthorized phone number')
            return False
            
        verification_check = twilio_client.verify.v2.services(
            os.getenv('TWILIO_VERIFY_SID')
        ).verification_checks.create(to=phone_number, code=code)
        
        return verification_check.status == 'approved'
    except TwilioRestException as e:
        st.error(f'Failed to verify OTP: {str(e)}')
        return False

def login_screen():
    st.title("🔐 Login Required")
    st.write("Please verify your phone number to continue")
    
    col1, col2 = st.columns(2)
    
    with col1:
        phone_number = st.text_input(
            "Phone Number",
            placeholder="+1234567890",
            key="phone_input"
        )
        
        if st.button("Send OTP"):
            if send_otp(phone_number):
                st.session_state.phone_verified = True
                st.success("OTP sent successfully!")
            else:
                st.error("Failed to send OTP")
    
    with col2:
        if st.session_state.phone_verified:
            otp_code = st.text_input(
                "Enter OTP",
                type="password",
                key="otp_input"
            )
            
            if st.button("Verify"):
                if check_otp(phone_number, otp_code):
                    st.session_state.authenticated = True
                    st.success("Authentication successful!")
                    time.sleep(1)
                    st.experimental_rerun()
                else:
                    st.error("Invalid OTP")

def render_grant_card(grant, current_page):
    with st.container():
        col1, col2, col3 = st.columns([2,1,1])
        
        with col1:
            st.markdown(f"### {grant['title']}")
            st.write(f"**Source:** {grant['source']}")
            
            if len(grant.get('description', '')) > 200:
                st.write(f"{grant['description'][:200]}...")
            else:
                st.write(grant.get('description', 'No description available'))
        
        with col2:
            display_grant_field("Amount", grant.get('amount', 'Not specified'))
            display_grant_field("Deadline", grant.get('deadline', 'Not specified'))
            display_grant_field("Category", grant.get('category', 'Not specified'))
        
        with col3:
            if st.button("View Details", key=f"view_{grant['_id']}"):
                st.session_state.selected_grant = grant
                st.session_state.previous_page = current_page
                st.session_state.page = 'grant_details'
                st.experimental_rerun()
            
            if st.button("Save Grant", key=f"save_{grant['_id']}"):
                if mongo_client.save_grant_for_user('default_user', str(grant['_id'])):
                    st.success("Grant saved successfully!")
                else:
                    st.error("Failed to save grant")
            
            if st.button("Send Alert", key=f"alert_{grant['_id']}"):
                if not mongo_client.check_alert_sent('default_user', grant['_id']):
                    if mongo_client.record_alert_sent('default_user', grant['_id'], 'app'):
                        st.success("Alert sent!")
                    else:
                        st.error("Failed to send alert")
                else:
                    st.info("Alert already sent for this grant")
        
        st.markdown("---")

def render_dashboard():
    st.title("📊 Grant Dashboard")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_grants = len(mongo_client.get_grants())
        st.metric("Total Grants", total_grants)
    
    with col2:
        recent_grants = len(mongo_client.get_grants(
            filters={'created_at': {'$gte': datetime.utcnow() - timedelta(days=7)}}
        ))
        st.metric("New This Week", recent_grants)
    
    with col3:
        saved_grants = len(mongo_client.get_saved_grants('default_user'))
        st.metric("Saved Grants", saved_grants)
    
    with col4:
        alerts_sent = len(mongo_client.get_alert_history_for_user('default_user'))
        st.metric("Alerts Sent", alerts_sent)
    
    # Recent Grants
    st.subheader("📥 Recent Grants")
    recent_grants = mongo_client.get_grants(
        sort_by=[('created_at', -1)],
        limit=5
    )
    
    for grant in recent_grants:
        render_grant_card(grant, 'dashboard')

def render_search():
    st.title("🔍 Search Grants")
    
    with st.form("search_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            keyword = st.text_input("Keywords", key="search_keyword")
            min_amount = st.number_input("Minimum Amount", min_value=0)
            max_amount = st.number_input("Maximum Amount", min_value=0)
        
        with col2:
            category = st.selectbox(
                "Category",
                ["All", "Research", "Technology", "Education", "Healthcare"]
            )
            
            deadline_range = st.selectbox(
                "Deadline",
                ["All", "This Week", "This Month", "Next 3 Months", "No Deadline"]
            )
        
        st.subheader("Sources")
        sources = mongo_client.get_sources_by_domain()
        
        col1, col2, col3, col4 = st.columns(4)
        selected_sources = []
        
        for i, source in enumerate(sources):
            with [col1, col2, col3, col4][i % 4]:
                if st.checkbox(source['name'], key=f"source_{source['_id']}"):
                    selected_sources.append(source['name'])
        
        submitted = st.form_submit_button("Search")
        
        if submitted:
            filters = {}
            
            if keyword:
                filters['$text'] = {'$search': keyword}
            
            if min_amount > 0:
                filters['amount'] = {'$gte': min_amount}
            
            if max_amount > 0:
                if 'amount' in filters:
                    filters['amount']['$lte'] = max_amount
                else:
                    filters['amount'] = {'$lte': max_amount}
            
            if category != "All":
                filters['category'] = category
            
            if selected_sources:
                filters['source'] = {'$in': selected_sources}
            
            if deadline_range != "All":
                now = datetime.utcnow()
                if deadline_range == "This Week":
                    filters['deadline'] = {'$lte': now + timedelta(days=7)}
                elif deadline_range == "This Month":
                    filters['deadline'] = {'$lte': now + timedelta(days=30)}
                elif deadline_range == "Next 3 Months":
                    filters['deadline'] = {'$lte': now + timedelta(days=90)}
                elif deadline_range == "No Deadline":
                    filters['deadline'] = None
            
            st.session_state.search_results = mongo_client.get_grants(filters=filters)
    
    if st.session_state.search_results:
        st.subheader(f"Found {len(st.session_state.search_results)} grants")
        for grant in st.session_state.search_results:
            render_grant_card(grant, 'search')
    elif submitted:
        st.info("No grants found matching your criteria")

def render_grant_details():
    if not st.session_state.selected_grant:
        st.error("No grant selected")
        return
    
    grant = st.session_state.selected_grant
    
    st.title(grant['title'])
    
    col1, col2 = st.columns([2,1])
    
    with col1:
        st.markdown("### Description")
        st.write(grant.get('description', 'No description available'))
        
        st.markdown("### Eligibility")
        st.write(grant.get('eligibility', 'No eligibility information available'))
        
        st.markdown("### How to Apply")
        st.write(grant.get('application_process', 'No application process information available'))
        
        if grant.get('url'):
            st.markdown(f"[Apply Now]({grant['url']})")
    
    with col2:
        st.markdown("### Grant Details")
        display_grant_field("Source", grant['source'])
        display_grant_field("Amount", grant.get('amount', 'Not specified'))
        display_grant_field("Deadline", grant.get('deadline', 'Not specified'))
        display_grant_field("Category", grant.get('category', 'Not specified'))
        display_grant_field("Location", grant.get('location', 'Not specified'))
        
        if st.button("Save Grant"):
            if mongo_client.save_grant_for_user('default_user', str(grant['_id'])):
                st.success("Grant saved successfully!")
            else:
                st.error("Failed to save grant")
        
        if st.button("Send Alert"):
            if not mongo_client.check_alert_sent('default_user', grant['_id']):
                if mongo_client.record_alert_sent('default_user', grant['_id'], 'app'):
                    st.success("Alert sent!")
                else:
                    st.error("Failed to send alert")
            else:
                st.info("Alert already sent for this grant")
    
    if st.button("Back"):
        st.session_state.page = st.session_state.previous_page
        st.session_state.selected_grant = None
        st.experimental_rerun()

def render_saved_grants():
    st.title("📌 Saved Grants")
    
    saved_grants = mongo_client.get_saved_grants('default_user')
    
    if not saved_grants:
        st.info("You haven't saved any grants yet")
        return
    
    for saved_grant in saved_grants:
        grant = saved_grant['grant_details']
        
        with st.container():
            col1, col2, col3 = st.columns([2,1,1])
            
            with col1:
                st.markdown(f"### {grant['title']}")
                st.write(f"**Source:** {grant['source']}")
                st.write(f"**Saved on:** {saved_grant['saved_at'].strftime('%Y-%m-%d %H:%M')}")
            
            with col2:
                display_grant_field("Amount", grant.get('amount', 'Not specified'))
                display_grant_field("Deadline", grant.get('deadline', 'Not specified'))
            
            with col3:
                if st.button("View Details", key=f"view_{grant['_id']}"):
                    st.session_state.selected_grant = grant
                    st.session_state.previous_page = 'saved_grants'
                    st.session_state.page = 'grant_details'
                    st.experimental_rerun()
                
                if st.button("Remove", key=f"remove_{grant['_id']}"):
                    if mongo_client.remove_saved_grant('default_user', str(grant['_id'])):
                        st.success("Grant removed from saved list")
                        time.sleep(1)
                        st.experimental_rerun()
                    else:
                        st.error("Failed to remove grant")
            
            st.markdown("---")

def render_alert_history():
    st.title("🔔 Alert History")
    
    alerts = mongo_client.get_alert_history_for_user('default_user')
    
    if not alerts:
        st.info("No alerts have been sent yet")
        return
    
    for alert in alerts:
        grant = alert['grant_details']
        
        with st.container():
            col1, col2 = st.columns([3,1])
            
            with col1:
                st.markdown(f"### {grant['title']}")
                st.write(f"**Source:** {grant['source']}")
                st.write(f"**Sent via:** {alert['channel']}")
                st.write(f"**Sent on:** {alert['timestamp'].strftime('%Y-%m-%d %H:%M')}")
            
            with col2:
                if st.button("View Grant", key=f"view_{grant['_id']}"):
                    st.session_state.selected_grant = grant
                    st.session_state.previous_page = 'alert_history'
                    st.session_state.page = 'grant_details'
                    st.experimental_rerun()
            
            st.markdown("---")

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
        
        if st.button("📌 Saved Grants"):
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
