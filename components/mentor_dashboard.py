import streamlit as st
from datetime import datetime
import pandas as pd
from models.database import DatabaseManager
from .charts import create_progress_chart, create_performance_metrics
from .chat import render_chat, render_chat_sidebar

def render_mentor_dashboard():
    st.title("Mentor Dashboard")
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Initialize chat state variables if they don't exist
    if 'chat_user' not in st.session_state:
        st.session_state['chat_user'] = None
    if 'chat_room' not in st.session_state:
        st.session_state['chat_room'] = None
    if 'active_tab' not in st.session_state:
        st.session_state['active_tab'] = 0
        
    # If a chat room or user is selected, switch to the chat tab
    if st.session_state.get('chat_room') or st.session_state.get('chat_user'):
        st.session_state['active_tab'] = 4  # Index of the chat tab (5th tab)
    
    # Create tabs for different sections with the active tab selected
    tab_names = ["📊 Overview", "👥 Interns", "📝 Tasks", "🎯 Categories", "💬 Chat"]
    active_tab_index = st.session_state.get('active_tab', 0)
    
    # Create the tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_names)
    
    # Use JavaScript to select the active tab
    if active_tab_index > 0:
        js = f"""
        <script>
            window.addEventListener('load', function() {{
                setTimeout(function() {{
                    document.querySelectorAll('.stTabs button[role="tab"]')[{active_tab_index}].click();
                }}, 100);
            }});
        </script>
        """
        st.components.v1.html(js, height=0)
    
    with tab1:
        st.header("Overall Progress")
        
        # Get all interns
        interns = db_manager.get_users_by_role("intern")
        
        # Calculate overall statistics
        total_interns = len(interns)
        active_interns = sum(1 for i in interns if db_manager.get_performance_metrics(i["email"]))
        total_tasks = sum(len(db_manager.get_user_tasks(i["email"])) for i in interns)
        completed_tasks = sum(
            len([t for t in db_manager.get_user_tasks(i["email"])
                 if t.get("progress", {}).get("status") == "done"])
            for i in interns
        )
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Interns", total_interns)
        with col2:
            st.metric("Active Interns", active_interns)
        with col3:
            st.metric("Total Tasks", total_tasks)
        with col4:
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            st.metric("Overall Completion", f"{completion_rate:.1f}%")
        
        # Show performance overview
        st.subheader("Performance Overview")
        performance_data = []
        for intern in interns:
            metrics = db_manager.get_performance_metrics(intern["email"])
            if metrics:
                performance_data.append({
                    "Intern": intern.get("name", intern["email"]),
                    "Tasks Completed": metrics.get("tasks_completed", 0),
                    "Streak Days": metrics.get("streak_days", 0),
                    "Avg Task Time": metrics.get("average_task_time", 0),
                    "Status": "Active" if metrics.get("tasks_completed", 0) > 0 else "Inactive"
                })
        
        if performance_data:
            df = pd.DataFrame(performance_data)
            st.dataframe(
                df.style.highlight_max(axis=0, color='lightgreen')
                       .highlight_min(axis=0, color='lightpink'),
                hide_index=True
            )
    
    with tab2:
        st.header("Intern Progress")
        
        # Intern selector
        selected_intern = st.selectbox(
            "Select Intern",
            options=[i["email"] for i in interns],
            format_func=lambda x: db_manager.get_user_name(x)
        )
        
        if selected_intern:
            intern_tasks = db_manager.get_user_tasks(selected_intern)
            metrics = db_manager.get_performance_metrics(selected_intern)
            
            # Show intern's performance metrics
            st.plotly_chart(
                create_performance_metrics(metrics),
                use_container_width=True
            )
            
            # Show task progress
            task_data = [
                {
                    "Task": t["title"],
                    "Progress": 100 if t.get("progress", {}).get("status") == "done" else 
                              50 if t.get("progress", {}).get("status") == "in_progress" else 0,
                    "Status": t.get("progress", {}).get("status", "Not Started").title(),
                    "Submission": t.get("progress", {}).get("submission_link", "None"),
                    "Time Spent": f"{(t.get('progress', {}).get('time_spent') or 0):.1f} hrs"
                }
                for t in intern_tasks
            ]
            
            if task_data:
                st.plotly_chart(
                    create_progress_chart(pd.DataFrame(task_data)),
                    use_container_width=True
                )
    
    with tab3:
        st.header("Task Management")
        
        # Task creation form
        with st.form("create_task"):
            st.subheader("Create New Task")
            task_title = st.text_input("Task Title")
            task_description = st.text_area("Task Description")
            task_category = st.selectbox(
                "Category",
                options=[cat["name"] for cat in db_manager.get_task_categories()]
            )
            
            col1, col2 = st.columns(2)
            with col1:
                assigned_to = st.multiselect(
                    "Assign to Interns",
                    options=[i["email"] for i in interns]
                )
            with col2:
                deadline = st.date_input("Deadline")
            
            # Resource links
            st.subheader("Resources")
            resource_titles = st.text_input("Resource Titles (comma-separated)")
            resource_urls = st.text_input("Resource URLs (comma-separated)")
            
            if st.form_submit_button("Create Task"):
                if task_title and task_description and assigned_to:
                    resources = []
                    if resource_titles and resource_urls:
                        titles = [t.strip() for t in resource_titles.split(",")]
                        urls = [u.strip() for u in resource_urls.split(",")]
                        resources = [{"title": t, "url": u} for t, u in zip(titles, urls)]
                    
                    for intern_email in assigned_to:
                        task_data = {
                            "title": task_title,
                            "description": task_description,
                            "category": task_category,
                            "assigned_to": intern_email,
                            "deadline": deadline,
                            "resources": resources,
                            "created_at": datetime.now()
                        }
                        db_manager.db.tasks.insert_one(task_data)
                    
                    st.success(f"Task created and assigned to {len(assigned_to)} intern(s)")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields")
    
    with tab4:
        st.header("Task Categories")
        
        # Category creation form
        with st.form("create_category"):
            st.subheader("Create New Category")
            category_name = st.text_input("Category Name")
            category_description = st.text_area("Category Description")
            category_color = st.color_picker("Category Color", "#1f77b4")
            
            if st.form_submit_button("Create Category"):
                if category_name and category_description:
                    db_manager.add_task_category(
                        category_name,
                        category_description,
                        category_color
                    )
                    st.success("Category created successfully!")
                    st.rerun()
                else:
                    st.error("Please fill in all fields")
        
        # Show existing categories
        st.subheader("Existing Categories")
        categories = db_manager.get_task_categories()
        for cat in categories:
            with st.expander(cat["name"]):
                st.write(cat["description"])
                st.color_picker("Color", cat["color"], disabled=True)
    
    with tab5:
        # Render chat interface based on whether we're in a room or direct message
        if st.session_state.get('chat_room'):
            render_chat(st.session_state["user"]["email"], None, st.session_state.get('chat_room'))
        else:
            render_chat(st.session_state["user"]["email"], st.session_state.get('chat_user'))
    
    # Render chat sidebar
    render_chat_sidebar(st.session_state["user"]["email"], "mentor")