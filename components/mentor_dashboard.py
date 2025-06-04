import streamlit as st
from supabase_client import get_supabase_client

supabase = get_supabase_client()

def render_mentor_dashboard():
    st.subheader("All Interns' Progress")
    # Fetch all users and their progress
    interns = supabase.table("users").select("*", "progress(task_id,status)").execute().data or []
    # Placeholder table
    st.write("## Interns Table")
    st.dataframe([
        {"Name": i.get('name', 'N/A'), "Email": i['email'], "Tasks Done": sum(1 for p in (i.get('progress') or []) if p['status'] == 'done')}
        for i in interns
    ])
    st.write("## Charts")
    st.info("[Charts (active/inactive, top performers) will appear here]")
    # TODO: Integrate Chart.js for visualizations 