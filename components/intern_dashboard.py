import streamlit as st
from mongodb_client import get_mongo_client
from datetime import datetime
import pandas as pd
from .charts import create_progress_chart, create_activity_timeline, create_progress_stats

def render_intern_dashboard(user_id, user_email):
    st.title("Intern Dashboard")
    
    # Get MongoDB connection
    mongo_client = get_mongo_client()
    db = mongo_client.progress_tracker
    
    # Fetch tasks and progress
    tasks = list(db.tasks.find({"assigned_to": user_email}))
    progress_records = list(db.progress.find({"user_email": user_email}))
    
    # Create progress lookup
    progress_lookup = {p["task_id"]: p for p in progress_records}
    
    # Calculate statistics
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if progress_lookup.get(str(t["_id"]), {}).get("status") == "done")
    
    # Show progress statistics
    create_progress_stats(total_tasks, completed_tasks)
    
    # Prepare data for charts
    chart_data = []
    timeline_data = []
    
    for task in tasks:
        task_id = str(task["_id"])
        progress = progress_lookup.get(task_id, {})
        status = progress.get("status", "Not Started")
        progress_value = 100 if status == "done" else 0
        
        chart_data.append({
            "Task": task["title"],
            "Progress": progress_value,
            "Status": status.title()
        })
        
        timeline_data.append({
            "Task": task["title"],
            "Start": progress.get("started_at", datetime.now()),
            "End": progress.get("completed_at", datetime.now() + pd.Timedelta(days=1)),
            "Status": status.title()
        })
    
    # Convert to DataFrames
    chart_df = pd.DataFrame(chart_data)
    timeline_df = pd.DataFrame(timeline_data)
    
    # Show charts
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(create_progress_chart(chart_df), use_container_width=True)
    with col2:
        st.plotly_chart(create_activity_timeline(timeline_df), use_container_width=True)
    
    # Tasks List
    st.header("Your Tasks")
    
    for task in tasks:
        task_id = str(task["_id"])
        progress = progress_lookup.get(task_id, {})
        status = progress.get("status", "Not Started")
        
        with st.expander(f"{task['title']} - {status.title()}", expanded=status=="Not Started"):
            st.write(task["description"])
            
            # Resources
            if task.get("resources"):
                st.write("**Resources:**")
                for resource in task["resources"]:
                    st.markdown(f"- [{resource['title']}]({resource['url']})")
            
            # Task actions
            col1, col2 = st.columns([3, 1])
            with col1:
                # Submission link
                current_link = progress.get("submission_link", "")
                new_link = st.text_input("Submission Link", 
                                       value=current_link,
                                       key=f"link_{task_id}")
                if new_link != current_link:
                    db.progress.update_one(
                        {"user_email": user_email, "task_id": task_id},
                        {
                            "$set": {
                                "submission_link": new_link,
                                "updated_at": datetime.now()
                            }
                        },
                        upsert=True
                    )
            
            with col2:
                # Mark as done button
                if status != "done":
                    if st.button("Mark as Done", key=f"done_{task_id}"):
                        db.progress.update_one(
                            {"user_email": user_email, "task_id": task_id},
                            {
                                "$set": {
                                    "status": "done",
                                    "completed_at": datetime.now(),
                                    "updated_at": datetime.now()
                                }
                            },
                            upsert=True
                        )
                        st.success("Marked as done!")
                        st.rerun()  # Updated from experimental_rerun to rerun
                else:
                    st.success("Completed!")
            
            st.divider()