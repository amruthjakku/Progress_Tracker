import streamlit as st
from datetime import datetime
import pandas as pd
from models.database import DatabaseManager
from .charts import (create_progress_chart, create_activity_timeline,
                    create_progress_stats, create_dependency_graph,
                    create_performance_metrics)
from .chat import render_chat, render_chat_sidebar

def render_intern_dashboard(user_id, user_email):
    st.title("Intern Dashboard")
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Progress", "📝 Tasks", "📈 Performance", "💬 Chat"
    ])
    
    # Get all necessary data
    tasks = db_manager.get_user_tasks(user_email)
    performance = db_manager.get_performance_metrics(user_email)
    
    with tab1:
        st.header("Your Progress")
        
        # Calculate statistics
        total_tasks = len(tasks)
        completed_tasks = sum(1 for t in tasks if t.get("progress", {}).get("status") == "done")
        
        # Show progress statistics
        create_progress_stats(total_tasks, completed_tasks)
        
        # Prepare data for charts
        chart_data = []
        timeline_data = []
        
        for task in tasks:
            progress = task.get("progress", {})
            status = progress.get("status", "Not Started")
            chart_data.append({
                "Task": task["title"],
                "Progress": 100 if status == "done" else (50 if status == "in_progress" else 0),
                "Status": status.title(),
                "Time Spent": f"{progress.get('time_spent', 0):.1f}hrs",
                "Last Updated": progress.get("updated_at", "Never")
            })
            
            if status != "Not Started":
                timeline_data.append({
                    "Task": task["title"],
                    "Start": progress.get("started_at", datetime.now()),
                    "End": progress.get("completed_at", datetime.now()),
                    "Status": status,
                    "Time Spent": f"{progress.get('time_spent', 0):.1f}hrs",
                    "Submission": progress.get("submission_link", "None")
                })
        
        # Show charts
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(
                create_progress_chart(pd.DataFrame(chart_data)),
                use_container_width=True
            )
        with col2:
            if timeline_data:
                st.plotly_chart(
                    create_activity_timeline(pd.DataFrame(timeline_data)),
                    use_container_width=True
                )
        
        # Show dependency graph
        st.plotly_chart(
            create_dependency_graph(tasks, db_manager.get_task_dependencies),
            use_container_width=True
        )
    
    with tab2:
        st.header("Your Tasks")
        
        # Task filtering
        col1, col2 = st.columns([2, 1])
        with col1:
            task_status = st.multiselect(
                "Filter by Status",
                ["Not Started", "In Progress", "Done"],
                default=["Not Started", "In Progress"]
            )
        with col2:
            task_category = st.selectbox(
                "Filter by Category",
                ["All"] + [cat["name"] for cat in db_manager.get_task_categories()]
            )
        
        filtered_tasks = [
            t for t in tasks
            if t.get("progress", {}).get("status", "Not Started").title() in task_status
            and (task_category == "All" or t.get("category") == task_category)
        ]
        
        for task in filtered_tasks:
            task_id = str(task["_id"])
            progress = task.get("progress", {})
            status = progress.get("status", "Not Started")
            
            with st.expander(
                f"📌 {task['title']} - {status.title()}",
                expanded=status=="Not Started"
            ):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(task["description"])
                    if task.get("resources"):
                        st.write("**Resources:**")
                        for resource in task["resources"]:
                            st.markdown(f"- [{resource['title']}]({resource['url']})")
                
                with col2:
                    # Show prerequisites if any
                    dependencies = db_manager.get_task_dependencies(task_id)
                    if dependencies:
                        st.write("**Prerequisites:**")
                        for dep, dep_status in dependencies.items():
                            st.write(f"- {dep}: {dep_status}")
                
                # Task actions
                col1, col2 = st.columns([3, 1])
                with col1:
                    current_link = progress.get("submission_link", "")
                    new_link = st.text_input(
                        "Submission Link",
                        value=current_link,
                        key=f"link_{task_id}"
                    )
                    if new_link != current_link:
                        db_manager.update_task_progress(
                            user_email,
                            task_id,
                            status="in_progress" if status == "Not Started" else status,
                            submission_link=new_link
                        )
                
                with col2:
                    if status == "done":
                        if st.button("✓ Unmark as Done", key=f"done_{task_id}", type="secondary"):
                            db_manager.update_task_progress(
                                user_email,
                                task_id,
                                "in_progress" if progress.get("submission_link") else "not_started",
                                progress.get("submission_link")
                            )
                            st.info("Task unmarked!")
                            st.rerun()
                    else:
                        if st.button("Mark as Done ✓", key=f"done_{task_id}", type="primary"):
                            db_manager.update_task_progress(
                                user_email,
                                task_id,
                                "done",
                                progress.get("submission_link")
                            )
                            st.success("Marked as done!")
                            st.rerun()
    
    with tab3:
        st.header("Your Performance")
        
        # Show performance metrics
        st.plotly_chart(
            create_performance_metrics(performance),
            use_container_width=True
        )
    
    with tab4:
        # Render chat interface
        render_chat(user_email, st.session_state.get('chat_user'))
    
    # Render chat sidebar
    render_chat_sidebar(user_email, "intern")