import streamlit as st
from datetime import datetime, time as dt_time

from utils.components import load_custom_css
from utils.heroku_manager import update_heroku_schedule, generate_cron_expression

# Load custom CSS
load_custom_css()

def render_notification_settings():
    """Render notification settings section."""
    st.subheader("Notification Settings")
    
    # Telegram settings
    st.markdown("### Telegram Notifications")
    
    # Get current Telegram chat ID
    current_chat_id = st.session_state.get('telegram_chat_id', '')
    
    new_chat_id = st.text_input(
        "Telegram Chat ID",
        value=current_chat_id,
        help="Enter your Telegram chat ID to receive notifications"
    )
    
    if new_chat_id != current_chat_id:
        st.session_state.telegram_chat_id = new_chat_id
        if new_chat_id:
            try:
                notifier = st.session_state.notifier
                test_result = notifier.send_telegram_message(
                    new_chat_id,
                    "👋 Test notification from Smart Grant Finder"
                )
                if test_result:
                    st.success("Test notification sent successfully!")
                else:
                    st.error("Failed to send test notification. Please check your chat ID.")
            except Exception as e:
                st.error(f"Error sending test notification: {str(e)}")

def render_search_preferences():
    """Render search preferences section."""
    st.subheader("Search Preferences")
    
    # Default minimum score
    default_min_score = st.slider(
        "Default Minimum Score",
        min_value=0,
        max_value=100,
        value=st.session_state.filters.get('min_score', 85),
        help="Set the default minimum score for grant recommendations"
    )
    
    # Default days to deadline
    default_days = st.number_input(
        "Default Days until Deadline",
        min_value=1,
        max_value=365,
        value=st.session_state.filters.get('days_to_deadline', 30),
        help="Set the default number of days until deadline for grant recommendations"
    )
    
    # Default categories
    categories = ['All', 'Technology', 'Healthcare', 'Education', 'Environment']
    default_categories = st.multiselect(
        "Default Categories",
        options=categories,
        default=st.session_state.filters.get('categories', ['All']),
        help="Set your preferred grant categories"
    )
    
    # Save preferences
    if st.button("Save Search Preferences"):
        st.session_state.filters.update({
            'min_score': default_min_score,
            'days_to_deadline': default_days,
            'categories': default_categories
        })
        st.success("Search preferences saved successfully!")

def render_schedule_settings():
    """Render schedule settings section."""
    st.subheader("Schedule Settings")
    
    # Schedule settings
    st.markdown("### Grant Search Schedule")
    
    # Frequency selection
    frequency_options = ["Daily", "Weekly", "Twice Weekly"]
    selected_frequency = st.selectbox(
        "Schedule Frequency",
        options=frequency_options,
        index=2,  # Default to "Twice Weekly"
        help="How often the grant search should run"
    )
    
    # Day selection for Weekly/Twice Weekly
    day_options = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    # Default to Monday and Thursday for "Twice Weekly"
    default_days = ["Monday", "Thursday"] if selected_frequency == "Twice Weekly" else \
                   ["Monday"] if selected_frequency == "Weekly" else []
    
    # Only show day selection for Weekly/Twice Weekly
    selected_days = []
    if selected_frequency in ["Weekly", "Twice Weekly"]:
        selected_days = st.multiselect(
            "Select days to run",
            options=day_options,
            default=default_days,
            help="Select the days when the grant search should run"
        )
    
    # Time selection
    selected_time = st.time_input(
        "Select search time",
        value=dt_time(10, 0),  # Default to 10:00 AM
        help="Select the time when the grant search should run"
    )
    
    # Convert time to string format
    time_str = selected_time.strftime("%H:%M")
    
    # Generate and display cron expression - Fix: Pass all required parameters
    cron_expression = generate_cron_expression(selected_frequency, selected_days, time_str)
    
    if cron_expression:
        st.code(cron_expression, language="text")
    else:
        st.warning("Could not generate a valid schedule. Please check your selections.")
    
    # Update schedule button
    if st.button("Update Schedule"):
        try:
            # Create settings dict with all required parameters
            schedule_settings = {
                'schedule_frequency': selected_frequency,
                'schedule_days': selected_days,
                'schedule_time': time_str
            }
            
            update_result = update_heroku_schedule(schedule_settings)
            
            if update_result:
                st.success("Schedule updated successfully!")
            else:
                st.error("Failed to update schedule. Please check Heroku configuration.")
        except Exception as e:
            st.error(f"Error updating schedule: {str(e)}")

def main():
    st.title("Settings")
    
    # Create tabs for different settings sections
    tab1, tab2, tab3 = st.tabs([
        "Notifications",
        "Search Preferences",
        "Schedule"
    ])
    
    with tab1:
        render_notification_settings()
    
    with tab2:
        render_search_preferences()
    
    with tab3:
        render_schedule_settings()
    
    # Display current version
    st.sidebar.markdown("---")
    st.sidebar.markdown("Version: 1.0.0")

if __name__ == "__main__":
    main() 