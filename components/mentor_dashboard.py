import streamlit as st
from datetime import datetime
import pandas as pd
import plotly.express as px
from models.database import DatabaseManager
from .charts import create_progress_chart, create_performance_metrics, create_dependency_graph
from .chat import render_chat, render_chat_sidebar
from .ai_assistant import render_ai_assistant
from .meetings import render_meetings_dashboard, render_meetings_sidebar
from .college_management import render_college_management

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
        st.session_state['active_tab'] = 7  # Index of the chat tab (8th tab)
    
    # Create tabs for different sections with the active tab selected
    tab_names = ["📊 Overview", "👥 Interns", "📝 Tasks", "🎯 Categories", "🏫 Colleges", "📍 Attendance", "🏆 Leaderboard", "💬 Chat", "📹 Meetings", "🤖 AI Settings"]
    active_tab_index = st.session_state.get('active_tab', 0)
    
    # Create the tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs(tab_names)
    
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
        st.header("Intern Management")
        
        # Create tabs for viewing and adding interns
        intern_tab1, intern_tab2 = st.tabs(["View Intern Progress", "Add New Intern"])
        
        with intern_tab1:
            # Intern selector
            selected_intern = st.selectbox(
                "Select Intern",
                options=[i["email"] for i in interns] if interns else [],
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
        
        with intern_tab2:
            st.subheader("Add New Intern")
            
            # Form for adding a new intern
            with st.form("add_intern_form"):
                intern_name = st.text_input("Intern Name")
                intern_email = st.text_input("Intern Email")
                
                # Optional fields
                st.subheader("Additional Information (Optional)")
                
                # Get colleges for dropdown
                colleges = db_manager.get_colleges()
                # Ensure all college names are strings and handle None values
                college_options = [""] + [str(college.get("name", "")) for college in colleges if college.get("name") is not None]
                
                col1, col2 = st.columns(2)
                with col1:
                    skills = st.text_input("Skills (comma-separated)")
                with col2:
                    selected_college = st.selectbox(
                        "College",
                        options=college_options,
                        format_func=lambda x: "Select college..." if x == "" else x
                    )
                
                submitted = st.form_submit_button("Add Intern")
                
                if submitted:
                    if intern_name and intern_email:
                        # Process skills
                        skills_list = [skill.strip() for skill in skills.split(",")] if skills else []
                        
                        # Create new intern using our method
                        result = db_manager.create_user(
                            email=intern_email,
                            name=intern_name,
                            role="intern",
                            skills=skills_list,
                            college=selected_college if selected_college else None
                        )
                        
                        if result:
                            st.success(f"Intern {intern_name} added successfully!")
                            st.rerun()
                        else:
                            st.error(f"User with email {intern_email} already exists or there was an error!")
                    else:
                        st.error("Please provide both name and email for the intern.")
    
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
                        result = db_manager.db.tasks.insert_one(task_data)
                        st.success(f"Task '{task_title}' created successfully!")
                    
                    st.success(f"Task created and assigned to {len(assigned_to)} intern(s)")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields")
        
        # Task Dependencies Management
        st.subheader("Manage Task Dependencies")
        st.write("""
        Set up dependencies between tasks to create a progression path for interns.
        A task can only be started when all its prerequisite tasks are completed.
        """)
        
        # Get all tasks for the dependency management UI
        all_tasks = db_manager.get_all_tasks()
        task_options = [f"{task['title']} ({task.get('assigned_to', 'unassigned')})" for task in all_tasks]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Add Dependency**")
            with st.form("add_dependency"):
                dependent_task = st.selectbox(
                    "Dependent Task (task that requires prerequisites)",
                    options=task_options,
                    key="dependent_task_add"
                )
                
                prerequisite_task = st.selectbox(
                    "Prerequisite Task (must be completed first)",
                    options=task_options,
                    key="prerequisite_task_add"
                )
                
                if st.form_submit_button("Add Dependency"):
                    if dependent_task and prerequisite_task and dependent_task != prerequisite_task:
                        # Extract task IDs from the options
                        dependent_idx = task_options.index(dependent_task)
                        prerequisite_idx = task_options.index(prerequisite_task)
                        
                        dependent_id = str(all_tasks[dependent_idx]["_id"])
                        prerequisite_id = str(all_tasks[prerequisite_idx]["_id"])
                        
                        # Add the dependency
                        result = db_manager.add_task_dependency(dependent_id, prerequisite_id)
                        if result:
                            st.success("Dependency added successfully!")
                        else:
                            st.error("Failed to add dependency.")
                    else:
                        st.error("Please select different tasks for dependent and prerequisite.")
        
        with col2:
            st.write("**Remove Dependency**")
            with st.form("remove_dependency"):
                # Get existing dependencies for the UI
                dependency_options = []
                for task in all_tasks:
                    task_id = str(task["_id"])
                    prereqs = db_manager.get_task_prerequisites(task_id)
                    for prereq in prereqs:
                        option = f"{task['title']} depends on {prereq['title']}"
                        dependency_options.append({
                            "label": option,
                            "task_id": task_id,
                            "prereq_id": str(prereq["_id"])
                        })
                
                if dependency_options:
                    selected_dependency = st.selectbox(
                        "Select Dependency to Remove",
                        options=[dep["label"] for dep in dependency_options],
                        key="dependency_remove"
                    )
                    
                    if st.form_submit_button("Remove Dependency"):
                        if selected_dependency:
                            # Find the selected dependency
                            idx = [dep["label"] for dep in dependency_options].index(selected_dependency)
                            dep = dependency_options[idx]
                            
                            # Remove the dependency
                            result = db_manager.remove_task_dependency(dep["task_id"], dep["prereq_id"])
                            if result:
                                st.success("Dependency removed successfully!")
                            else:
                                st.error("Failed to remove dependency.")
                        else:
                            st.error("Please select a dependency to remove.")
                else:
                    st.info("No dependencies found. Add some dependencies first.")
                    st.form_submit_button("Remove Dependency", disabled=True)
        
        # Task dependency visualization
        st.subheader("📊 Task Dependency Overview")
        
        with st.expander("ℹ️ About Task Dependencies", expanded=True):
            st.markdown("""
            This visualization shows the relationships between all tasks in the system:
            
            - **Green nodes**: Completed tasks
            - **Blue nodes**: Tasks in progress
            - **Red nodes**: Tasks not yet started
            
            Use this map to:
            - Identify bottlenecks in the intern progression
            - See which tasks are blocking the most interns
            - Plan new task assignments based on prerequisites
            """)
        
        # Get all tasks for visualization
        all_tasks = db_manager.get_all_tasks()
        
        # Show task status summary
        total_tasks = len(all_tasks)
        completed_count = sum(1 for t in all_tasks if any(
            p.get("status") == "done" for p in t.get("progress", [])
        ))
        in_progress_count = sum(1 for t in all_tasks if any(
            p.get("status") == "in_progress" for p in t.get("progress", [])
        ))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Tasks", total_tasks)
        with col2:
            st.metric("Tasks In Progress", in_progress_count)
        with col3:
            st.metric("Tasks Completed", completed_count)
        
        # Show the dependency graph for all tasks
        if all_tasks:
            # For the mentor view, we need to modify the task status to reflect overall progress
            for task in all_tasks:
                # Check if any intern has completed this task
                progress_statuses = [p.get("status", "not_started") for p in task.get("progress", [])]
                if "done" in progress_statuses:
                    task["progress"] = {"status": "done"}
                elif "in_progress" in progress_statuses:
                    task["progress"] = {"status": "in_progress"}
                else:
                    task["progress"] = {"status": "not_started"}
            
            # Show the enhanced dependency graph
            st.plotly_chart(
                create_dependency_graph(all_tasks, db_manager.get_task_dependencies),
                use_container_width=True
            )
            
            # Identify potential bottlenecks
            bottleneck_tasks = []
            for task in all_tasks:
                # Count how many tasks depend on this one
                dependent_count = sum(1 for t in all_tasks if str(task["_id"]) in t.get("prerequisites", []))
                if dependent_count > 1 and task.get("progress", {}).get("status") != "done":
                    bottleneck_tasks.append({
                        "title": task["title"],
                        "id": str(task["_id"]),
                        "status": task.get("progress", {}).get("status", "not_started"),
                        "blocks": dependent_count
                    })
            
            # Sort bottlenecks by number of tasks they block
            bottleneck_tasks.sort(key=lambda x: x["blocks"], reverse=True)
            
            if bottleneck_tasks:
                st.subheader("🚧 Potential Bottlenecks")
                st.warning("These tasks are blocking progress for multiple dependent tasks:")
                
                # Create a table of bottlenecks
                bottleneck_data = []
                for task in bottleneck_tasks[:5]:  # Show top 5 bottlenecks
                    status_emoji = "🔴" if task["status"] == "not_started" else "🔵"
                    bottleneck_data.append({
                        "Task": f"{status_emoji} {task['title']}",
                        "Status": task["status"].replace("_", " ").title(),
                        "Blocks": f"{task['blocks']} tasks"
                    })
                
                st.table(pd.DataFrame(bottleneck_data))
    
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
        render_college_management()
        
    with tab6:
        st.header("📍 Attendance Tracking")
        
        # Create tabs for attendance views
        attendance_tabs = st.tabs(["📊 Overview", "📅 Daily Records", "📈 Statistics", "🔒 IP Management"])
        
        with attendance_tabs[0]:
            st.subheader("Attendance Overview")
            
            # Get attendance statistics
            attendance_stats = db_manager.get_attendance_stats(days=30)
            
            if attendance_stats:
                # Create a DataFrame for the attendance statistics
                stats_data = []
                for stat in attendance_stats:
                    stats_data.append({
                        "Intern": stat["intern_name"],
                        "Email": stat["intern_email"],
                        "Days Present": stat["days_present"],
                        "Days Absent": stat["days_absent"],
                        "Attendance Rate": f"{stat['attendance_rate']:.1f}%",
                        "Avg Hours": f"{stat['avg_hours']:.2f}",
                        "On-time Days": stat["on_time_days"],
                        "Late Days": stat["late_days"],
                        "Punctuality": f"{stat['punctuality_rate']:.1f}%"
                    })
                
                stats_df = pd.DataFrame(stats_data)
                st.dataframe(stats_df, use_container_width=True)
                
                # Create attendance rate chart
                if len(stats_data) > 0:
                    chart_data = pd.DataFrame({
                        "Intern": [stat["intern_name"] for stat in attendance_stats],
                        "Attendance Rate": [stat["attendance_rate"] for stat in attendance_stats],
                        "Punctuality Rate": [stat["punctuality_rate"] for stat in attendance_stats]
                    })
                    
                    fig = px.bar(
                        chart_data,
                        x="Intern",
                        y=["Attendance Rate", "Punctuality Rate"],
                        title="Attendance & Punctuality Rates",
                        labels={"value": "Rate (%)", "variable": "Metric"},
                        barmode="group"
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No attendance data available yet.")
        
        with attendance_tabs[1]:
            st.subheader("Daily Attendance Records")
            
            # Date range selector
            col1, col2 = st.columns(2)
            with col1:
                days = st.slider("Days to show", min_value=7, max_value=90, value=30, step=1)
            with col2:
                selected_intern = st.selectbox(
                    "Filter by Intern",
                    options=["All Interns"] + [intern["name"] for intern in db_manager.get_users_by_role("intern")],
                    key="attendance_intern_filter"
                )
            
            # Get attendance history
            if selected_intern == "All Interns":
                attendance_history = db_manager.get_attendance_history(days=days)
            else:
                # Find the intern's email
                intern = next((i for i in db_manager.get_users_by_role("intern") if i["name"] == selected_intern), None)
                if intern:
                    attendance_history = db_manager.get_attendance_history(intern_email=intern["email"], days=days)
                else:
                    attendance_history = []
            
            if attendance_history:
                # Create a DataFrame for the attendance history
                history_data = []
                for record in attendance_history:
                    history_data.append({
                        "Date": record["date"].strftime("%Y-%m-%d"),
                        "Intern": record.get("intern_name", record["intern_email"]) if "intern_name" in record else record["intern_email"],
                        "Check In": record["check_in"].strftime("%I:%M %p") if record["check_in"] else "N/A",
                        "Check Out": record["check_out"].strftime("%I:%M %p") if record["check_out"] else "N/A",
                        "Duration (hours)": f"{record['duration']:.2f}" if record["duration"] else "N/A",
                        "Status": record["status"],
                        "IP Address": record.get("ip_address", "N/A"),
                        "Verification": "✅ IP Verified" if record.get("verification_method") == "ip_based" else "N/A"
                    })
                
                history_df = pd.DataFrame(history_data)
                st.dataframe(history_df, use_container_width=True)
                
                # Download button
                csv = history_df.to_csv(index=False)
                st.download_button(
                    label="Download as CSV",
                    data=csv,
                    file_name=f"attendance_report_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No attendance records found for the selected period.")
        
        with attendance_tabs[2]:
            st.subheader("Attendance Analytics")
            
            # Get attendance statistics
            attendance_stats = db_manager.get_attendance_stats(days=30)
            
            if attendance_stats:
                # Create charts
                col1, col2 = st.columns(2)
                
                with col1:
                    # Present vs Absent chart
                    present_absent_data = pd.DataFrame({
                        "Intern": [stat["intern_name"] for stat in attendance_stats],
                        "Present": [stat["days_present"] for stat in attendance_stats],
                        "Absent": [stat["days_absent"] for stat in attendance_stats]
                    })
                    
                    fig1 = px.bar(
                        present_absent_data,
                        x="Intern",
                        y=["Present", "Absent"],
                        title="Present vs Absent Days",
                        labels={"value": "Days", "variable": "Status"},
                        barmode="stack"
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col2:
                    # On-time vs Late chart
                    ontime_late_data = pd.DataFrame({
                        "Intern": [stat["intern_name"] for stat in attendance_stats],
                        "On-time": [stat["on_time_days"] for stat in attendance_stats],
                        "Late": [stat["late_days"] for stat in attendance_stats]
                    })
                    
                    fig2 = px.bar(
                        ontime_late_data,
                        x="Intern",
                        y=["On-time", "Late"],
                        title="On-time vs Late Days",
                        labels={"value": "Days", "variable": "Status"},
                        barmode="stack"
                    )
                    st.plotly_chart(fig2, use_container_width=True)
                
                # Average hours chart
                avg_hours_data = pd.DataFrame({
                    "Intern": [stat["intern_name"] for stat in attendance_stats],
                    "Average Hours": [stat["avg_hours"] for stat in attendance_stats]
                })
                
                fig3 = px.bar(
                    avg_hours_data,
                    x="Intern",
                    y="Average Hours",
                    title="Average Hours per Day",
                    labels={"Average Hours": "Hours", "Intern": "Intern"},
                    color="Average Hours",
                    color_continuous_scale="Viridis"
                )
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("No attendance data available for analytics.")
                
        with attendance_tabs[3]:
            st.subheader("IP-Based Attendance Verification")
            
            # Get current user's email for logging changes
            user_email = st.session_state.get('user_email', 'admin@example.com')
            
            # Introduction
            st.markdown("""
            ### IP-Based Attendance Verification System
            
            This system allows interns to mark attendance only when connected to approved networks or IP addresses.
            Use this interface to manage the allowed networks and IP addresses.
            
            **How it works:**
            1. Interns can only check in/out when connected to an allowed network
            2. Each attendance record captures IP address and device information
            3. Attendance logs show verification status
            """)
            
            # Get current network info for testing
            from utils.network import get_network_info
            current_network = get_network_info()
            
            # Display current network info
            st.subheader("Your Current Network")
            col1, col2 = st.columns(2)
            with col1:
                st.info(f"IP Address: **{current_network.get('ip', 'Unknown')}**")
                if current_network.get('ssid'):
                    st.info(f"WiFi Network: **{current_network.get('ssid')}**")
            with col2:
                st.info(f"Device: **{current_network.get('hostname', 'Unknown')}**")
                st.info(f"Platform: **{current_network.get('platform', 'Unknown')}**")
            
            # Get allowed networks from database
            allowed_networks = db_manager.get_allowed_networks()
            
            # Display current allowed networks
            st.subheader("Currently Allowed Networks")
            
            # WiFi Networks (SSIDs)
            with st.expander("WiFi Networks (SSIDs)", expanded=True):
                ssid_list = allowed_networks.get("ssid", [])
                if ssid_list:
                    for i, ssid in enumerate(ssid_list):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**{i+1}.** {ssid}")
                        with col2:
                            if st.button("Remove", key=f"remove_ssid_{i}"):
                                if db_manager.remove_allowed_network("ssid", ssid, user_email):
                                    st.success(f"Removed WiFi network: {ssid}")
                                    st.rerun()
                                else:
                                    st.error("Failed to remove network")
                else:
                    st.write("No WiFi networks configured")
                
                # Add new SSID
                with st.form("add_ssid_form"):
                    st.subheader("Add WiFi Network")
                    new_ssid = st.text_input("WiFi Network Name (SSID)")
                    submit = st.form_submit_button("Add WiFi Network")
                    
                    if submit and new_ssid:
                        if db_manager.add_allowed_network("ssid", new_ssid, user_email):
                            st.success(f"Added WiFi network: {new_ssid}")
                            st.rerun()
                        else:
                            st.error("Failed to add network")
            
            # IP Addresses (Exact)
            with st.expander("Exact IP Addresses", expanded=True):
                ip_list = allowed_networks.get("ip_exact", [])
                if ip_list:
                    for i, ip in enumerate(ip_list):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**{i+1}.** {ip}")
                        with col2:
                            if st.button("Remove", key=f"remove_ip_exact_{i}"):
                                if db_manager.remove_allowed_network("ip_exact", ip, user_email):
                                    st.success(f"Removed IP address: {ip}")
                                    st.rerun()
                                else:
                                    st.error("Failed to remove IP address")
                else:
                    st.write("No exact IP addresses configured")
                
                # Add new IP
                with st.form("add_ip_exact_form"):
                    st.subheader("Add Exact IP Address")
                    new_ip = st.text_input("IP Address (e.g., 192.168.1.100)")
                    
                    # Add current IP button
                    col1, col2 = st.columns(2)
                    with col1:
                        submit = st.form_submit_button("Add IP Address")
                    with col2:
                        use_current = st.form_submit_button(f"Use Current IP ({current_network.get('ip', 'Unknown')})")
                    
                    if submit and new_ip:
                        if db_manager.add_allowed_network("ip_exact", new_ip, user_email):
                            st.success(f"Added IP address: {new_ip}")
                            st.rerun()
                        else:
                            st.error("Failed to add IP address")
                    
                    if use_current and current_network.get('ip') != 'Unknown':
                        if db_manager.add_allowed_network("ip_exact", current_network.get('ip'), user_email):
                            st.success(f"Added current IP address: {current_network.get('ip')}")
                            st.rerun()
                        else:
                            st.error("Failed to add IP address")
            
            # IP Ranges (Prefix)
            with st.expander("IP Ranges (Prefix)", expanded=True):
                ip_ranges = allowed_networks.get("ip_ranges", [])
                if ip_ranges:
                    for i, ip_range in enumerate(ip_ranges):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**{i+1}.** {ip_range}* (matches all IPs starting with this prefix)")
                        with col2:
                            if st.button("Remove", key=f"remove_ip_range_{i}"):
                                if db_manager.remove_allowed_network("ip_ranges", ip_range, user_email):
                                    st.success(f"Removed IP range: {ip_range}")
                                    st.rerun()
                                else:
                                    st.error("Failed to remove IP range")
                else:
                    st.write("No IP ranges configured")
                
                # Add new IP range
                with st.form("add_ip_range_form"):
                    st.subheader("Add IP Range (Prefix)")
                    new_ip_range = st.text_input("IP Prefix (e.g., 192.168.1.)")
                    submit = st.form_submit_button("Add IP Range")
                    
                    if submit and new_ip_range:
                        if db_manager.add_allowed_network("ip_ranges", new_ip_range, user_email):
                            st.success(f"Added IP range: {new_ip_range}")
                            st.rerun()
                        else:
                            st.error("Failed to add IP range")
            
            # CIDR Notation
            with st.expander("CIDR Notation", expanded=True):
                ip_cidr = allowed_networks.get("ip_cidr", [])
                if ip_cidr:
                    for i, cidr in enumerate(ip_cidr):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.write(f"**{i+1}.** {cidr}")
                        with col2:
                            if st.button("Remove", key=f"remove_ip_cidr_{i}"):
                                if db_manager.remove_allowed_network("ip_cidr", cidr, user_email):
                                    st.success(f"Removed CIDR range: {cidr}")
                                    st.rerun()
                                else:
                                    st.error("Failed to remove CIDR range")
                else:
                    st.write("No CIDR ranges configured")
                
                # Add new CIDR
                with st.form("add_ip_cidr_form"):
                    st.subheader("Add CIDR Range")
                    new_cidr = st.text_input("CIDR Notation (e.g., 192.168.0.0/16)")
                    submit = st.form_submit_button("Add CIDR Range")
                    
                    if submit and new_cidr:
                        if db_manager.add_allowed_network("ip_cidr", new_cidr, user_email):
                            st.success(f"Added CIDR range: {new_cidr}")
                            st.rerun()
                        else:
                            st.error("Failed to add CIDR range")
            
            # Testing section
            st.subheader("Test IP Verification")
            test_ip = st.text_input("Enter an IP address to test", value=current_network.get('ip', ''))
            if st.button("Test IP"):
                # Create a test network info object
                test_network = {"ip": test_ip}
                
                # Check if the IP is allowed
                from utils.network import is_on_allowed_network
                
                # Test with a mock network info that has just the IP
                is_allowed = False
                for ip_type in ["ip_exact", "ip_ranges", "ip_cidr"]:
                    if ip_type in allowed_networks:
                        if ip_type == "ip_exact" and test_ip in allowed_networks["ip_exact"]:
                            is_allowed = True
                            break
                        elif ip_type == "ip_ranges":
                            for prefix in allowed_networks["ip_ranges"]:
                                if test_ip.startswith(prefix):
                                    is_allowed = True
                                    break
                        elif ip_type == "ip_cidr":
                            try:
                                import ipaddress
                                ip_obj = ipaddress.ip_address(test_ip)
                                for cidr in allowed_networks["ip_cidr"]:
                                    if ip_obj in ipaddress.ip_network(cidr):
                                        is_allowed = True
                                        break
                            except:
                                pass
                
                if is_allowed:
                    st.success(f"✅ The IP address {test_ip} is allowed for attendance marking")
                else:
                    st.error(f"❌ The IP address {test_ip} is NOT allowed for attendance marking")
                    
                # Suggest adding if not allowed
                if not is_allowed:
                    st.info("To allow this IP, use one of the forms above to add it to the allowed list.")
    
    with tab7:
        st.header("Intern Leaderboard")
        
        # Get leaderboard data using our new method
        leaderboard_data = db_manager.get_intern_leaderboard()
        
        if leaderboard_data:
            # Convert to DataFrame for display
            leaderboard_df = pd.DataFrame([
                {
                    "Intern": intern["name"],
                    "Email": intern["email"],
                    "College": intern["college"],
                    "Tasks Completed": intern["tasks_completed"],
                    "Total Tasks": intern["total_tasks"],
                    "Completion %": round(intern["completion_percentage"], 1),
                    "Streak Days": intern["streak_days"],
                    "Avg Task Time (hrs)": round(intern["avg_task_time"], 1)
                }
                for intern in leaderboard_data
            ])
            
            # Display leaderboard
            st.dataframe(
                leaderboard_df.style.highlight_max(subset=["Completion %", "Tasks Completed", "Streak Days"], 
                                                  color='lightgreen'),
                hide_index=True,
                use_container_width=True
            )
            
            # Add a medal system for top performers
            if len(leaderboard_df) >= 3:
                st.subheader("🏆 Top Performers")
                col1, col2, col3 = st.columns(3)
                
                with col2:  # First place (center)
                    st.markdown(f"### 🥇 First Place")
                    st.markdown(f"**{leaderboard_df.iloc[0]['Intern']}**")
                    st.markdown(f"College: **{leaderboard_df.iloc[0]['College']}**")
                    st.markdown(f"Completion: **{leaderboard_df.iloc[0]['Completion %']}%**")
                    st.markdown(f"Tasks: **{leaderboard_df.iloc[0]['Tasks Completed']}/{leaderboard_df.iloc[0]['Total Tasks']}**")
                
                with col1:  # Second place (left)
                    st.markdown(f"### 🥈 Second Place")
                    st.markdown(f"**{leaderboard_df.iloc[1]['Intern']}**")
                    st.markdown(f"College: **{leaderboard_df.iloc[1]['College']}**")
                    st.markdown(f"Completion: **{leaderboard_df.iloc[1]['Completion %']}%**")
                    st.markdown(f"Tasks: **{leaderboard_df.iloc[1]['Tasks Completed']}/{leaderboard_df.iloc[1]['Total Tasks']}**")
                
                with col3:  # Third place (right)
                    st.markdown(f"### 🥉 Third Place")
                    st.markdown(f"**{leaderboard_df.iloc[2]['Intern']}**")
                    st.markdown(f"College: **{leaderboard_df.iloc[2]['College']}**")
                    st.markdown(f"Completion: **{leaderboard_df.iloc[2]['Completion %']}%**")
                    st.markdown(f"Tasks: **{leaderboard_df.iloc[2]['Tasks Completed']}/{leaderboard_df.iloc[2]['Total Tasks']}**")
            
            # Visualize leaderboard as a bar chart
            fig = px.bar(
                leaderboard_df,
                x="Intern",
                y="Completion %",
                color="Completion %",
                title="Intern Progress Leaderboard",
                labels={"Completion %": "Completion Percentage", "Intern": "Intern Name"},
                color_continuous_scale=px.colors.sequential.Viridis,
                hover_data=["Tasks Completed", "Total Tasks", "Streak Days"]
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            
            # Add a line chart to show progress over time (if we had historical data)
            st.subheader("Leaderboard Metrics")
            metric_option = st.selectbox(
                "Select Metric to Visualize",
                ["Completion %", "Tasks Completed", "Streak Days", "Avg Task Time (hrs)"]
            )
            
            fig2 = px.bar(
                leaderboard_df,
                x="Intern",
                y=metric_option,
                color=metric_option,
                title=f"Intern {metric_option} Comparison",
                color_continuous_scale=px.colors.sequential.Plasma
            )
            fig2.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No intern data available for the leaderboard.")
            
            # Show a sample of what the leaderboard will look like
            st.subheader("Sample Leaderboard (Add interns to see real data)")
            sample_data = pd.DataFrame([
                {"Intern": "Sample Intern 1", "Completion %": 85, "Tasks Completed": 17, "Total Tasks": 20},
                {"Intern": "Sample Intern 2", "Completion %": 70, "Tasks Completed": 14, "Total Tasks": 20},
                {"Intern": "Sample Intern 3", "Completion %": 55, "Tasks Completed": 11, "Total Tasks": 20},
            ])
            st.dataframe(sample_data, hide_index=True)
    
    with tab6:
        # Render chat interface based on whether we're in a room or direct message
        if st.session_state.get('chat_room'):
            render_chat(st.session_state["user"]["email"], None, st.session_state.get('chat_room'))
        else:
            render_chat(st.session_state["user"]["email"], st.session_state.get('chat_user'))
    
    with tab7:
        # Render meetings dashboard
        render_meetings_dashboard(st.session_state["user"]["email"])
        
    with tab8:
        st.header("AI Assistant Settings")
        
        # AI model selection
        st.subheader("AI Model Configuration")
        
        # Initialize settings in session state if not exists
        if 'ai_settings' not in st.session_state:
            st.session_state.ai_settings = {
                "model": "mistralai/Mistral-7B-Instruct-v0.2",
                "api_key": "",
                "enabled": True,
                "custom_instructions": ""
            }
        
        # Model selection
        model_options = {
            "mistralai/Mistral-7B-Instruct-v0.2": "Mistral 7B (Default)",
            "meta-llama/Llama-2-7b-chat-hf": "Llama 2 7B",
            "google/gemini-pro": "Google Gemini Pro",
            "custom": "Custom Model"
        }
        
        selected_model = st.selectbox(
            "Select AI Model",
            options=list(model_options.keys()),
            format_func=lambda x: model_options[x],
            index=list(model_options.keys()).index(st.session_state.ai_settings["model"]) 
                if st.session_state.ai_settings["model"] in model_options else 0
        )
        
        # Custom model input if "custom" is selected
        if selected_model == "custom":
            custom_model = st.text_input("Enter Custom Model ID", 
                                        value="" if st.session_state.ai_settings["model"] not in model_options 
                                              else st.session_state.ai_settings["model"])
            if custom_model:
                selected_model = custom_model
        
        # API key input
        api_key = st.text_input(
            "Hugging Face API Token (optional)",
            value=st.session_state.ai_settings.get("api_key", ""),
            type="password",
            help="Enter your Hugging Face API token for better performance. Leave empty to use the default configuration."
        )
        
        # Enable/disable AI assistant
        enable_ai = st.checkbox(
            "Enable AI Assistant for Interns",
            value=st.session_state.ai_settings.get("enabled", True),
            help="When enabled, interns will have access to the AI assistant for help with their tasks."
        )
        
        # Custom instructions for the AI
        st.subheader("Custom Instructions")
        custom_instructions = st.text_area(
            "Add custom instructions for the AI assistant",
            value=st.session_state.ai_settings.get("custom_instructions", ""),
            height=150,
            help="These instructions will be included with every prompt to guide the AI's responses."
        )
        
        # Save settings button
        if st.button("Save AI Settings"):
            st.session_state.ai_settings = {
                "model": selected_model,
                "api_key": api_key,
                "enabled": enable_ai,
                "custom_instructions": custom_instructions
            }
            
            # Save settings to database
            try:
                db_manager.db.ai_settings.update_one(
                    {"setting_type": "global"},
                    {"$set": {
                        "model": selected_model,
                        "enabled": enable_ai,
                        "custom_instructions": custom_instructions,
                        "updated_at": datetime.now(),
                        "updated_by": st.session_state["user"]["email"]
                    }},
                    upsert=True
                )
                st.success("AI settings saved successfully!")
            except Exception as e:
                st.error(f"Error saving settings: {str(e)}")
        
        # Test the AI assistant
        st.subheader("Test AI Assistant")
        test_prompt = st.text_input("Enter a test prompt")
        if test_prompt and st.button("Test"):
            with st.spinner("Getting AI response..."):
                # Create a sample user context
                sample_context = {
                    "tasks_completed": 5,
                    "total_tasks": 10,
                    "progress": "50%",
                    "current_tasks": ["Sample Task 1", "Sample Task 2"],
                    "streak_days": 3
                }
                
                # Try to get a response using the current settings
                try:
                    from utils.huggingface_chatbot import HuggingFaceChatbot
                    
                    # Initialize chatbot with current settings
                    chatbot = HuggingFaceChatbot(
                        model_id=selected_model,
                        api_token=api_key if api_key else None
                    )
                    
                    # Format prompt with custom instructions
                    enhanced_prompt = f"""
                    {custom_instructions}
                    
                    Context about the user:
                    - Tasks completed: 5 out of 10
                    - Current progress: 50%
                    - Current tasks: Sample Task 1, Sample Task 2
                    - Streak days: 3
                    
                    User question: {test_prompt}
                    
                    Please provide a helpful response.
                    """
                    
                    # Get response
                    response = chatbot.get_response(enhanced_prompt)
                    
                    # Display response
                    st.subheader("AI Response:")
                    st.write(response)
                except Exception as e:
                    # Fallback to Gemini API
                    try:
                        from utils.gemini_api import get_gemini_response
                        response = get_gemini_response(f"You are an AI assistant for interns. Answer this question: {test_prompt}")
                        st.subheader("AI Response (via Gemini fallback):")
                        st.write(response)
                    except Exception as ex:
                        st.error(f"Error testing AI: {str(ex)}")
        
        # Usage statistics
        st.subheader("AI Assistant Usage Statistics")
        try:
            # Get usage statistics from database
            ai_interactions = list(db_manager.db.ai_interactions.find().sort("timestamp", -1).limit(100))
            
            if ai_interactions:
                # Count interactions by user
                user_counts = {}
                for interaction in ai_interactions:
                    user_email = interaction.get("user_email", "unknown")
                    user_counts[user_email] = user_counts.get(user_email, 0) + 1
                
                # Display statistics
                st.write(f"Total interactions: {len(ai_interactions)}")
                st.write(f"Unique users: {len(user_counts)}")
                
                # Show recent interactions
                st.write("Recent interactions:")
                for i, interaction in enumerate(ai_interactions[:5]):
                    with st.expander(f"Interaction {i+1} - {interaction.get('timestamp', 'Unknown time')}"):
                        st.write(f"User: {interaction.get('user_email', 'Unknown')}")
                        st.write(f"Query: {interaction.get('user_query', 'Unknown')}")
                        st.write(f"Response: {interaction.get('ai_response', 'Unknown')}")
            else:
                st.info("No AI interactions recorded yet.")
        except Exception as e:
            st.error(f"Error retrieving usage statistics: {str(e)}")
    
    # Render chat sidebar
    render_chat_sidebar(st.session_state["user"]["email"], "mentor")
    
    # Render meetings sidebar
    render_meetings_sidebar(st.session_state["user"]["email"])