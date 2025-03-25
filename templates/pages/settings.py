import streamlit as st
from typing import Dict

from database.mongodb_client import MongoDBClient
from database.pinecone_client import PineconeClient

# Initialize clients
mongodb_client = MongoDBClient()
pinecone_client = PineconeClient()

st.set_page_config(
    page_title="Settings - Kevin's Smart Grant Finder",
    page_icon="⚙️"
)

def load_priorities() -> Dict:
    """Load current priority settings."""
    return mongodb_client.get_priorities()

def save_priorities(priorities: Dict) -> bool:
    """Save and update priority settings."""
    # Save to MongoDB
    if not mongodb_client.store_priorities(priorities):
        return False
    
    # Update Pinecone vectors
    return pinecone_client.store_priority_vectors(priorities)

def main():
    st.title("⚙️ Settings")
    
    # Load current priorities
    current_priorities = load_priorities()
    
    with st.form("priorities_form"):
        st.subheader("Grant Priority Settings")
        
        # Category weights
        st.write("Category Weights")
        categories = {
            "federal": st.slider(
                "Federal Grants",
                0.0, 1.0,
                current_priorities.get("categories", {}).get("federal", 0.8)
            ),
            "state": st.slider(
                "State Grants",
                0.0, 1.0,
                current_priorities.get("categories", {}).get("state", 0.7)
            ),
            "nonprofit": st.slider(
                "Nonprofit Grants",
                0.0, 1.0,
                current_priorities.get("categories", {}).get("nonprofit", 0.6)
            )
        }
        
        # Keywords
        st.write("\nKeywords by Category")
        keywords = {}
        
        # Federal keywords
        federal_keywords = st.text_area(
            "Federal Grant Keywords (one per line)",
            value="\n".join(current_priorities.get("keywords", {}).get("federal", [])),
            height=100
        )
        keywords["federal"] = [k.strip() for k in federal_keywords.split("\n") if k.strip()]
        
        # State keywords
        state_keywords = st.text_area(
            "State Grant Keywords (one per line)",
            value="\n".join(current_priorities.get("keywords", {}).get("state", [])),
            height=100
        )
        keywords["state"] = [k.strip() for k in state_keywords.split("\n") if k.strip()]
        
        # Nonprofit keywords
        nonprofit_keywords = st.text_area(
            "Nonprofit Grant Keywords (one per line)",
            value="\n".join(current_priorities.get("keywords", {}).get("nonprofit", [])),
            height=100
        )
        keywords["nonprofit"] = [k.strip() for k in nonprofit_keywords.split("\n") if k.strip()]
        
        # Notification settings
        st.subheader("Notification Settings")
        notifications = {
            "email": st.checkbox(
                "Email Notifications",
                value=current_priorities.get("notifications", {}).get("email", True)
            ),
            "sms": st.checkbox(
                "SMS Notifications",
                value=current_priorities.get("notifications", {}).get("sms", True)
            ),
            "telegram": st.checkbox(
                "Telegram Notifications",
                value=current_priorities.get("notifications", {}).get("telegram", True)
            )
        }
        
        # Submit button
        submitted = st.form_submit_button("Save Settings")
        
        if submitted:
            # Prepare priorities data
            priorities_data = {
                "categories": categories,
                "keywords": keywords,
                "notifications": notifications,
                "updated_at": datetime.utcnow()
            }
            
            # Save priorities
            if save_priorities(priorities_data):
                st.success("Settings saved successfully!")
            else:
                st.error("Failed to save settings. Please try again.")

if __name__ == "__main__":
    main()