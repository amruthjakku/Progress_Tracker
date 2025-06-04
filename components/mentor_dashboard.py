import streamlit as st
from mongodb_client import get_mongo_client
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from .charts import create_progress_chart, create_activity_timeline, create_progress_stats

def render_mentor_dashboard():
    st.title("Mentor Dashboard 👥")
    
    # Get MongoDB connection
    mongo_client = get_mongo_client()
    db = mongo_client.progress_tracker
    
    # Overall Progress Section
    st.header("Overall Progress")
    
    # Get all interns and their tasks
    interns = db.tasks.distinct("assigned_to")
    
    # Calculate progress for each intern
    intern_progress = []
    for email in interns:
        tasks = list(db.tasks.find({"assigned_to": email}))
        progress = list(db.progress.find({"user_email": email}))
        progress_lookup = {p["task_id"]: p for p in progress}
        
        completed = sum(1 for t in tasks if progress_lookup.get(str(t["_id"]), {}).get("status") == "done")
        total = len(tasks)
        last_active = max([p.get("updated_at", datetime.min) for p in progress] or [datetime.min])
        
        intern_progress.append({
            "Email": email,
            "Completed": completed,
            "Total": total,
            "Progress": (completed / total * 100) if total > 0 else 0,
            "Last Active": last_active,
            "Status": "Active" if datetime.now() - last_active < timedelta(days=7) else "Inactive"
        })
    
    df = pd.DataFrame(intern_progress)
    
    # Summary metrics
    total_interns = len(interns)
    active_interns = sum(1 for p in intern_progress if p["Status"] == "Active")
    avg_progress = df["Progress"].mean()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Interns", total_interns)
    with col2:
        st.metric("Active Interns", active_interns)
    with col3:
        st.metric("Average Progress", f"{avg_progress:.1f}%")
    
    # Progress visualization
    col1, col2 = st.columns(2)
    
    with col1:
        # Progress bar chart
        fig_progress = px.bar(
            df,
            x="Email",
            y="Progress",
            color="Status",
            title="Intern Progress Overview",
            labels={"Progress": "Completion %"}
        )
        st.plotly_chart(fig_progress, use_container_width=True)
    
    with col2:
        # Active vs Inactive pie chart
        status_counts = df["Status"].value_counts()
        fig_status = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="Active vs Inactive Interns"
        )
        st.plotly_chart(fig_status, use_container_width=True)
    
    # Detailed Progress Table
    st.header("Detailed Progress")
    
    # Convert datetime to string for display
    df["Last Active"] = df["Last Active"].apply(lambda x: x.strftime("%Y-%m-%d %H:%M"))
    
    st.dataframe(
        df.sort_values("Progress", ascending=False),
        hide_index=True,
        column_config={
            "Progress": st.column_config.ProgressColumn(
                "Progress",
                help="Percentage of tasks completed",
                format="%d%%",
                min_value=0,
                max_value=100,
            ),
            "Last Active": st.column_config.DatetimeColumn(
                "Last Active",
                help="Last activity timestamp"
            )
        }
    )
    
    # Individual Intern Details
    st.header("Individual Intern Details")
    selected_intern = st.selectbox("Select Intern", interns)
    
    if selected_intern:
        st.subheader(f"Tasks for {selected_intern}")
        
        tasks = list(db.tasks.find({"assigned_to": selected_intern}))
        progress = list(db.progress.find({"user_email": selected_intern}))
        progress_lookup = {p["task_id"]: p for p in progress}
        
        for task in tasks:
            task_id = str(task["_id"])
            task_progress = progress_lookup.get(task_id, {})
            status = task_progress.get("status", "Not Started")
            
            with st.expander(f"{task['title']} - {status.title()}"):
                st.write(task["description"])
                
                if task.get("resources"):
                    st.write("**Resources:**")
                    for resource in task["resources"]:
                        st.markdown(f"- [{resource['title']}]({resource['url']})")
                
                if task_progress.get("submission_link"):
                    st.write("**Submission:**", task_progress["submission_link"])
                
                if task_progress.get("completed_at"):
                    st.write("**Completed:**", task_progress["completed_at"].strftime("%Y-%m-%d %H:%M"))
                elif task_progress.get("started_at"):
                    st.write("**Started:**", task_progress["started_at"].strftime("%Y-%m-%d %H:%M"))