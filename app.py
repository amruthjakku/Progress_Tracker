import streamlit as st
import os
import sys
from mongodb_client import get_mongo_client
# from supabase_client import get_supabase_client  # Remove supabase
from components.intern_dashboard import render_intern_dashboard
from components.mentor_dashboard import render_mentor_dashboard

# Set Streamlit configuration to bypass onboarding and show address in terminal
os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'false'
os.environ['STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION'] = 'false'
os.environ['STREAMLIT_SERVER_ENABLE_CORS'] = 'false'
os.environ['STREAMLIT_GLOBAL_DEVELOPMENT_MODE'] = 'false'
os.environ['STREAMLIT_GLOBAL_SHOW_WARNING_ON_DIRECT_EXECUTION'] = 'false'
os.environ['STREAMLIT_GLOBAL_DISABLE_WATCHDOG_WARNING'] = 'true'

# Create .streamlit directory if it doesn't exist
streamlit_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.streamlit')
os.makedirs(streamlit_dir, exist_ok=True)

# Create credentials.toml to bypass onboarding
credentials_path = os.path.join(streamlit_dir, 'credentials.toml')
if not os.path.exists(credentials_path):
    with open(credentials_path, 'w') as f:
        f.write('[general]\nemail = ""\n')

# Print a message to make the localhost address more visible in the terminal
print("\n" + "="*50)
print("STREAMLIT APP RUNNING AT: http://localhost:8501")
print("="*50 + "\n")

st.set_page_config(page_title="Intern Progress Tracker", page_icon="🚀", layout="wide")

mongo_client = get_mongo_client()
db = mongo_client["progress_tracker"]

# --- Auth (Google) ---
if 'user' not in st.session_state:
    st.session_state['user'] = None

if st.session_state['user'] is None:
    st.title("Intern Progress Tracker 🚀")
    st.write("""
    **Track your internship progress, access resources, and keep your mentor updated!**
    
    - Interns: Mark tasks as done, submit links, and see your progress.
    - Mentors: View all interns' progress and activity.
    """)
    # Supabase Auth UI (Google)
    col1, col2 = st.columns([2,1])
    with col1:
        role = st.selectbox("Simulate login as:", ["intern", "mentor"])
    with col2:
        login_btn = st.button("Login with Google")
    if login_btn:
        st.info("[Google Auth via Supabase should be implemented here]")
        # TODO: Implement Google Auth (Streamlit can't natively do this, so use a workaround or custom component)
        # For now, simulate login
        email = f"{role}@example.com"
        st.session_state['user'] = {'email': email, 'role': role}
        st.rerun()
    st.stop()

user = st.session_state['user']
role = user.get('role', 'intern')

# --- Sidebar Navigation ---
st.sidebar.title(f"Welcome, {user['email']}")
if role == 'mentor':
    page = st.sidebar.radio("Go to", ["Mentor Dashboard", "Logout"])
else:
    page = st.sidebar.radio("Go to", ["Intern Dashboard", "Logout"])

if page == "Logout":
    st.session_state['user'] = None
    st.rerun()

# --- Main Content ---
if page == "Intern Dashboard":
    # Fetch user_id from users collection
    user_data = db.users.find_one({"email": user['email']}, {"_id": 1})
    user_id = str(user_data["_id"]) if user_data else None
    render_intern_dashboard(user_id, user['email'])
elif page == "Mentor Dashboard":
    render_mentor_dashboard()

# --- Footer ---
st.markdown("""
---
<center>Made with 🚀 by [Your Name or Org](https://github.com/your-repo)</center>
""", unsafe_allow_html=True)