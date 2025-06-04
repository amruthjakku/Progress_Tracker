import streamlit as st
from mongodb_client import get_mongo_client
# from supabase_client import get_supabase_client  # Remove supabase
from components.intern_dashboard import render_intern_dashboard
from components.mentor_dashboard import render_mentor_dashboard

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