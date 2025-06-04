import streamlit as st
from supabase_client import get_supabase_client
from components.intern_dashboard import render_intern_dashboard
from components.mentor_dashboard import render_mentor_dashboard

st.set_page_config(page_title="Intern Progress Tracker", page_icon="🚀", layout="wide")

supabase = get_supabase_client()

# --- Auth (Google) ---
if 'user' not in st.session_state:
    st.session_state['user'] = None

if st.session_state['user'] is None:
    st.title("Intern Progress Tracker 🚀")
    st.write("Login with your Google account to continue.")
    # Supabase Auth UI (Google)
    login_btn = st.button("Login with Google")
    if login_btn:
        st.info("[Google Auth via Supabase should be implemented here]")
        # TODO: Implement Google Auth (Streamlit can't natively do this, so use a workaround or custom component)
        # For now, simulate login
        st.session_state['user'] = {'email': 'intern@example.com', 'role': 'intern'}
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
    # Fetch user_id from users table
    user_data = supabase.table("users").select("id").eq("email", user['email']).execute().data
    user_id = user_data[0]['id'] if user_data else None
    render_intern_dashboard(user_id, user['email'])
elif page == "Mentor Dashboard":
    render_mentor_dashboard() 