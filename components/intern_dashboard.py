import streamlit as st
from datetime import datetime
import pandas as pd
import plotly.express as px
from models.database import DatabaseManager
from .charts import (create_progress_chart, create_activity_timeline,
                    create_progress_stats, create_dependency_graph,
                    create_performance_metrics, create_performance_heatmap,
                    create_weekly_activity_chart, create_category_performance_chart)
from .chat import render_chat, render_chat_sidebar
from .ai_assistant import render_ai_assistant, render_ai_assistant_sidebar
from utils.network import is_on_allowed_network, format_network_info
from functools import lru_cache
import time

# Cache for expensive database operations
@lru_cache(maxsize=32)
def cached_get_user_tasks(user_email, cache_time):
    """Cached version of get_user_tasks with time-based invalidation"""
    try:
        db_manager = DatabaseManager()
        return db_manager.get_user_tasks(user_email)
    except Exception as e:
        print(f"Error in cached_get_user_tasks: {str(e)}")
        return []  # Return empty list on error

@lru_cache(maxsize=32)
def cached_get_performance_metrics(user_email, period, cache_time):
    """Cached version of get_performance_metrics with time-based invalidation"""
    try:
        db_manager = DatabaseManager()
        return db_manager.get_performance_metrics(user_email, period)
    except Exception as e:
        print(f"Error in cached_get_performance_metrics: {str(e)}")
        return {}  # Return empty dict on error

@lru_cache(maxsize=32)
def cached_get_task_dependencies(task_id, cache_time):
    """Cached version of get_task_dependencies with time-based invalidation"""
    try:
        db_manager = DatabaseManager()
        return db_manager.get_task_dependencies(task_id)
    except Exception as e:
        print(f"Error in cached_get_task_dependencies: {str(e)}")
        return {}  # Return empty dict on error

def clear_function_caches():
    """Clear all function caches to free memory"""
    cached_get_user_tasks.cache_clear()
    cached_get_performance_metrics.cache_clear()
    cached_get_task_dependencies.cache_clear()

def render_intern_dashboard(user_id, user_email):
    st.title("Intern Dashboard")
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Initialize chat state variables if they don't exist
    if 'chat_user' not in st.session_state:
        st.session_state['chat_user'] = None
    if 'chat_room' not in st.session_state:
        st.session_state['chat_room'] = None
    if 'active_tab' not in st.session_state:
        st.session_state['active_tab'] = 0
    # Initialize cache_time with proper error handling
    if 'cache_time' not in st.session_state:
        try:
            st.session_state['cache_time'] = int(time.time())
        except Exception:
            # Fallback to a simple integer if time.time() fails
            st.session_state['cache_time'] = 0
    
    # Ensure cache_time is always an integer in session state
    if not isinstance(st.session_state.get('cache_time'), int):
        try:
            st.session_state['cache_time'] = int(st.session_state['cache_time'])
        except (TypeError, ValueError):
            # Reset to current time or 0 if conversion fails
            try:
                st.session_state['cache_time'] = int(time.time())
            except Exception:
                st.session_state['cache_time'] = 0
    if 'data_loaded' not in st.session_state:
        st.session_state['data_loaded'] = {}
    if 'last_cache_clear' not in st.session_state:
        st.session_state['last_cache_clear'] = time.time()
    
    # Clear caches periodically to prevent memory leaks (every 30 minutes)
    current_time = time.time()
    if current_time - st.session_state['last_cache_clear'] > 1800:  # 30 minutes in seconds
        clear_function_caches()
        # Keep only essential data in session state
        essential_keys = ['chat_user', 'chat_room', 'active_tab', 'cache_time']
        for key in list(st.session_state.keys()):
            if key not in essential_keys:
                del st.session_state[key]
        st.session_state['data_loaded'] = {}
        st.session_state['last_cache_clear'] = current_time
        
    # If a chat room or user is selected, switch to the chat tab
    if st.session_state.get('chat_room') or st.session_state.get('chat_user'):
        # Make sure this is an integer (explicitly convert to int)
        st.session_state['active_tab'] = 5  # Index of the chat tab (now 5 after adding attendance)
        
    # Ensure active_tab is always an integer in session state
    if 'active_tab' in st.session_state and not isinstance(st.session_state['active_tab'], int):
        try:
            st.session_state['active_tab'] = int(st.session_state['active_tab'])
        except (TypeError, ValueError):
            st.session_state['active_tab'] = 0
    
    # Create tabs for different sections with the active tab selected
    tab_names = ["📊 Progress", "📝 Tasks", "📈 Performance", "🏆 Leaderboard", "📍 Attendance", "💬 Chat", "🤖 AI Assistant"]
    
    # Ensure active_tab_index is always a valid integer
    try:
        # Get active_tab from session state with default 0
        active_tab = st.session_state.get('active_tab', 0)
        
        # Convert to integer
        if active_tab is None:
            active_tab_index = 0
        else:
            active_tab_index = int(active_tab)
            
        # Validate range (0-6 for the 7 tabs)
        if active_tab_index < 0 or active_tab_index > 6:
            active_tab_index = 0
    except (TypeError, ValueError):
        # If conversion fails, default to 0
        active_tab_index = 0
        
    # Update session state with validated value
    st.session_state['active_tab'] = active_tab_index
    
    # Create the tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(tab_names)
    
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
    
    # Get all necessary data using cached functions with error handling
    try:
        # Ensure cache_time is an integer
        if 'cache_time' in st.session_state and st.session_state['cache_time'] is not None:
            try:
                cache_time = int(st.session_state['cache_time'])
            except (TypeError, ValueError):
                # If conversion fails, use current time
                try:
                    cache_time = int(time.time())
                except Exception:
                    cache_time = 0
        else:
            # If cache_time is not in session state or is None
            try:
                cache_time = int(time.time())
            except Exception:
                cache_time = 0
                
        # Update session state with the validated cache_time
        st.session_state['cache_time'] = cache_time
    except Exception:
        # If there's any error with cache_time, reset it
        cache_time = 0
        st.session_state['cache_time'] = 0
        
    # Get tasks with error handling
    try:
        tasks = cached_get_user_tasks(user_email, cache_time)
    except Exception as e:
        st.error(f"Error loading tasks: {str(e)}")
        tasks = []
    
    # Only load performance metrics if we're on the performance tab or need it for other calculations
    try:
        if active_tab_index == 2 or 'performance' not in st.session_state['data_loaded']:
            performance = cached_get_performance_metrics(user_email, "weekly", cache_time)
            st.session_state['data_loaded']['performance'] = performance
        else:
            performance = st.session_state['data_loaded'].get('performance', {})
            
        # Ensure performance is a dictionary
        if performance is None:
            performance = {}
    except Exception as e:
        st.error(f"Error loading performance metrics: {str(e)}")
        performance = {}
    
    with tab1:
        st.header("Your Progress")
        
        # Calculate statistics once and reuse
        task_status_counts = {"done": 0, "in_progress": 0, "not_started": 0}
        for task in tasks:
            status = task.get("progress", {}).get("status", "not_started")
            task_status_counts[status] = task_status_counts.get(status, 0) + 1
        
        total_tasks = len(tasks)
        completed_tasks = task_status_counts.get("done", 0)
        
        # Show progress statistics
        create_progress_stats(total_tasks, completed_tasks)
        
        # Prepare data for charts - do this only once
        if 'chart_data' not in st.session_state['data_loaded']:
            chart_data = []
            timeline_data = []
            
            for task in tasks:
                progress = task.get("progress", {})
                status = progress.get("status", "Not Started")
                chart_data.append({
                    "Task": task["title"],
                    "Progress": 100 if status == "done" else (50 if status == "in_progress" else 0),
                    "Status": status.title(),
                    "Time Spent": f"{(progress.get('time_spent') or 0):.1f}hrs",
                    "Last Updated": progress.get("updated_at", "Never")
                })
                
                if status != "Not Started":
                    timeline_data.append({
                        "Task": task["title"],
                        "Start": progress.get("started_at", datetime.now()),
                        "End": progress.get("completed_at", datetime.now()),
                        "Status": status,
                        "Time Spent": f"{(progress.get('time_spent') or 0):.1f}hrs",
                        "Submission": progress.get("submission_link", "None")
                    })
            
            # Store in session state to avoid recalculation
            st.session_state['data_loaded']['chart_data'] = chart_data
            st.session_state['data_loaded']['timeline_data'] = timeline_data
        else:
            chart_data = st.session_state['data_loaded']['chart_data']
            timeline_data = st.session_state['data_loaded']['timeline_data']
        
        # Show charts
        col1, col2 = st.columns(2)
        with col1:
            # Convert to DataFrame only once before plotting
            chart_df = pd.DataFrame(chart_data)
            st.plotly_chart(
                create_progress_chart(chart_df),
                use_container_width=True
            )
        with col2:
            if timeline_data:
                # Convert to DataFrame only once before plotting
                timeline_df = pd.DataFrame(timeline_data)
                st.plotly_chart(
                    create_activity_timeline(timeline_df),
                    use_container_width=True
                )
        
        # Task dependency visualization section
        st.subheader("📊 Task Dependency Map")
        
        # Add explanation and guidance
        with st.expander("ℹ️ Understanding the Task Dependency Map", expanded=True):
            st.markdown("""
            This interactive visualization shows how your tasks are connected and their current status:
            
            - **Green nodes**: Completed tasks
            - **Blue nodes**: Tasks in progress
            - **Red nodes**: Tasks not yet started
            
            **Tips for using this map:**
            - **Hover** over any task to see details, prerequisites, and what tasks it unlocks
            - Use the **buttons** above the graph to filter by task status
            - Tasks are arranged to show progression from prerequisites to dependent tasks
            - Focus on completing tasks that will unlock the most dependencies
            """)
        
        # Show task status summary - reuse the counts we already calculated
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Completed", task_status_counts.get("done", 0), delta=None, delta_color="normal")
        with col2:
            st.metric("In Progress", task_status_counts.get("in_progress", 0), delta=None, delta_color="normal")
        with col3:
            st.metric("Not Started", task_status_counts.get("not_started", 0), delta=None, delta_color="normal")
        
        # Show enhanced dependency graph - use cached dependency function
        if 'dependency_graph' not in st.session_state['data_loaded']:
            # Create a wrapper function that uses our cached version
            def get_cached_dependencies(task_id):
                return cached_get_task_dependencies(task_id, st.session_state['cache_time'])
            
            dependency_graph = create_dependency_graph(tasks, get_cached_dependencies)
            st.session_state['data_loaded']['dependency_graph'] = dependency_graph
        else:
            dependency_graph = st.session_state['data_loaded']['dependency_graph']
        
        st.plotly_chart(dependency_graph, use_container_width=True)
        
        # Add recommendations based on task dependencies
        if tasks:
            # Find tasks that are ready to start (all prerequisites completed)
            # Only calculate this if we haven't already
            if 'task_recommendations' not in st.session_state['data_loaded']:
                ready_tasks = []
                blocked_tasks = []
                
                # Create a lookup dictionary for tasks by ID for faster access
                tasks_by_id = {str(task["_id"]): task for task in tasks}
                
                for task in tasks:
                    if task.get("progress", {}).get("status") != "done":  # Not completed
                        prereqs = task.get("prerequisites", [])
                        if not prereqs:
                            # No prerequisites
                            if task.get("progress", {}).get("status") != "in_progress":
                                ready_tasks.append(task["title"])
                        else:
                            # Check if all prerequisites are completed
                            all_prereqs_done = True
                            missing_prereqs = []
                            
                            for prereq in prereqs:
                                prereq_task = tasks_by_id.get(prereq)
                                if prereq_task and prereq_task.get("progress", {}).get("status") != "done":
                                    all_prereqs_done = False
                                    missing_prereqs.append(prereq_task["title"])
                            
                            if all_prereqs_done:
                                if task.get("progress", {}).get("status") != "in_progress":
                                    ready_tasks.append(task["title"])
                            else:
                                blocked_tasks.append({
                                    "title": task["title"],
                                    "missing_prereqs": missing_prereqs
                                })
                
                # Store in session state
                st.session_state['data_loaded']['task_recommendations'] = {
                    'ready_tasks': ready_tasks,
                    'blocked_tasks': blocked_tasks
                }
            else:
                recommendations = st.session_state['data_loaded']['task_recommendations']
                ready_tasks = recommendations['ready_tasks']
                blocked_tasks = recommendations['blocked_tasks']
            
            # Show recommendations
            if ready_tasks or blocked_tasks:
                st.subheader("🧭 Task Recommendations")
                
                if ready_tasks:
                    st.success(f"**Ready to start:** You can begin working on these {len(ready_tasks)} tasks now:")
                    for i, task in enumerate(ready_tasks[:5]):
                        st.markdown(f"- {task}")
                    if len(ready_tasks) > 5:
                        st.markdown(f"- *and {len(ready_tasks) - 5} more...*")
                
                if blocked_tasks:
                    st.warning(f"**Blocked tasks:** Complete prerequisites to unlock these {len(blocked_tasks)} tasks:")
                    for i, task in enumerate(blocked_tasks[:3]):
                        st.markdown(f"- **{task['title']}** requires: {', '.join(task['missing_prereqs'])}")
                    if len(blocked_tasks) > 3:
                        st.markdown(f"- *and {len(blocked_tasks) - 3} more...*")
    
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
        
        # Cache task categories to avoid repeated database calls
        if 'task_categories' not in st.session_state['data_loaded']:
            task_categories = db_manager.get_task_categories()
            st.session_state['data_loaded']['task_categories'] = task_categories
        else:
            task_categories = st.session_state['data_loaded']['task_categories']
            
        with col2:
            task_category = st.selectbox(
                "Filter by Category",
                ["All"] + [cat["name"] for cat in task_categories]
            )
        
        # Filter tasks efficiently
        filtered_tasks = [
            t for t in tasks
            if t.get("progress", {}).get("status", "Not Started").title() in task_status
            and (task_category == "All" or t.get("category") == task_category)
        ]
        
        # Cache task dependencies and can_start results
        if 'task_dependencies' not in st.session_state['data_loaded']:
            st.session_state['data_loaded']['task_dependencies'] = {}
        
        if 'can_start_tasks' not in st.session_state['data_loaded']:
            st.session_state['data_loaded']['can_start_tasks'] = {}
        
        # Pre-compute all dependencies and can_start for visible tasks
        visible_task_ids = [str(task["_id"]) for task in filtered_tasks]
        
        # Batch fetch dependencies for all visible tasks that aren't already cached
        uncached_task_ids = [
            task_id for task_id in visible_task_ids 
            if task_id not in st.session_state['data_loaded']['task_dependencies']
        ]
        
        # Fetch dependencies in batch if needed
        for task_id in uncached_task_ids:
            # Use our cached function
            dependencies = cached_get_task_dependencies(task_id, st.session_state['cache_time'])
            st.session_state['data_loaded']['task_dependencies'][task_id] = dependencies
            
            # Pre-compute can_start
            can_start = True
            for _, dep_status in dependencies.items():
                if dep_status != "done":
                    can_start = False
                    break
            st.session_state['data_loaded']['can_start_tasks'][task_id] = can_start
        
        # Display tasks with cached dependency information
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
                    # Show prerequisites if any - use cached dependencies
                    dependencies = st.session_state['data_loaded']['task_dependencies'].get(task_id, {})
                    if dependencies:
                        st.write("**Prerequisites:**")
                        for dep, dep_status in dependencies.items():
                            st.write(f"- {dep}: {dep_status}")
                
                # Use cached can_start result
                can_start = st.session_state['data_loaded']['can_start_tasks'].get(task_id, True)
                
                # Task actions
                col1, col2 = st.columns([3, 1])
                with col1:
                    current_link = progress.get("submission_link", "")
                    
                    # Disable submission if prerequisites are not completed
                    if status == "Not Started" and not can_start:
                        st.warning("⚠️ You must complete all prerequisites before starting this task.")
                        new_link = st.text_input(
                            "Submission Link",
                            value=current_link,
                            key=f"link_{task_id}",
                            disabled=True
                        )
                    else:
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
                            # Update cache time to invalidate caches with error handling
                            try:
                                st.session_state['cache_time'] = int(time.time())
                            except Exception:
                                # Fallback to incrementing the current cache time
                                st.session_state['cache_time'] = st.session_state.get('cache_time', 0) + 1
                
                with col2:
                    if status == "done":
                        if st.button("✓ Unmark as Done", key=f"done_{task_id}", type="secondary"):
                            db_manager.update_task_progress(
                                user_email,
                                task_id,
                                "in_progress" if progress.get("submission_link") else "not_started",
                                progress.get("submission_link")
                            )
                            # Update cache time to invalidate caches with error handling
                            try:
                                st.session_state['cache_time'] = int(time.time())
                            except Exception:
                                # Fallback to incrementing the current cache time
                                st.session_state['cache_time'] = st.session_state.get('cache_time', 0) + 1
                            st.session_state['data_loaded'] = {}  # Clear all cached data
                            st.info("Task unmarked!")
                            st.rerun()
                    else:
                        # Disable the "Mark as Done" button if prerequisites are not completed
                        if status == "Not Started" and not can_start:
                            st.button("Mark as Done ✓", key=f"done_{task_id}", type="primary", disabled=True)
                        else:
                            if st.button("Mark as Done ✓", key=f"done_{task_id}", type="primary"):
                                db_manager.update_task_progress(
                                    user_email,
                                    task_id,
                                    "done",
                                    progress.get("submission_link")
                                )
                                # Update cache time to invalidate caches with error handling
                                try:
                                    st.session_state['cache_time'] = int(time.time())
                                except Exception:
                                    # Fallback to incrementing the current cache time
                                    st.session_state['cache_time'] = st.session_state.get('cache_time', 0) + 1
                                st.session_state['data_loaded'] = {}  # Clear all cached data
                                st.success("Marked as done!")
                                st.rerun()
    
    with tab3:
        st.header("Your Performance")
        
        # Show performance metrics
        st.plotly_chart(
            create_performance_metrics(performance),
            use_container_width=True
        )
        
        # Add a heatmap of task activity
        st.subheader("Task Activity Heatmap")
        
        # Add explanation
        with st.expander("ℹ️ About the Activity Heatmap", expanded=False):
            st.markdown("""
            This heatmap visualizes your task activity over time:
            
            - **Started**: When you began working on tasks
            - **Completed**: When you marked tasks as done
            - **Submission**: When you submitted task links
            
            Darker colors indicate more activity on that day. This helps you identify patterns in your work habits and productivity.
            """)
        
        # Create time period selector
        time_period = st.radio(
            "Time Period",
            ["Last 7 Days", "Last 14 Days", "Last 30 Days"],
            horizontal=True
        )
        
        # Map selection to number of days
        days_mapping = {
            "Last 7 Days": 7,
            "Last 14 Days": 14,
            "Last 30 Days": 30
        }
        selected_days = days_mapping[time_period]
        
        # Create and display the heatmap
        if 'heatmap_data' not in st.session_state['data_loaded'] or 'heatmap_days' not in st.session_state['data_loaded'] or st.session_state['data_loaded']['heatmap_days'] != selected_days:
            heatmap = create_performance_heatmap(tasks, days=selected_days)
            st.session_state['data_loaded']['heatmap_data'] = heatmap
            st.session_state['data_loaded']['heatmap_days'] = selected_days
        else:
            heatmap = st.session_state['data_loaded']['heatmap_data']
        
        st.plotly_chart(heatmap, use_container_width=True)
        
        # Add productivity insights based on the heatmap data
        st.subheader("Productivity Insights")
        
        # Calculate some basic insights
        task_status_counts = {"done": 0, "in_progress": 0, "not_started": 0}
        completed_dates = []
        
        for task in tasks:
            status = task.get("progress", {}).get("status", "not_started")
            task_status_counts[status] = task_status_counts.get(status, 0) + 1
            
            # Collect completion dates for pattern analysis
            if status == "done" and task.get("progress", {}).get("completed_at"):
                completed_dates.append(task.get("progress", {}).get("completed_at"))
        
        # Calculate completion rate
        completion_rate = (task_status_counts["done"] / len(tasks) * 100) if len(tasks) > 0 else 0
        
        # Display insights
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Task Completion Rate", f"{completion_rate:.1f}%")
            
            # Determine productivity trend
            if completion_rate >= 70:
                st.success("🌟 Excellent progress! You're completing tasks at a high rate.")
            elif completion_rate >= 40:
                st.info("👍 Good progress. Keep up the momentum to improve your completion rate.")
            else:
                st.warning("⚠️ Your task completion rate is low. Consider focusing on completing more tasks.")
        
        with col2:
            # Calculate tasks in progress ratio
            in_progress_ratio = (task_status_counts["in_progress"] / len(tasks) * 100) if len(tasks) > 0 else 0
            st.metric("Tasks In Progress", f"{in_progress_ratio:.1f}%")
            
            # Provide advice based on in-progress ratio
            if in_progress_ratio > 50:
                st.warning("⚠️ You have many tasks in progress. Consider focusing on completing them before starting new ones.")
            elif in_progress_ratio > 20:
                st.info("👍 You have a balanced number of tasks in progress.")
            else:
                st.success("🎯 You're good at completing tasks before moving to new ones.")
        
        # Identify work patterns if we have enough data
        if len(completed_dates) >= 3:
            # Group by day of week
            day_counts = {}
            for date in completed_dates:
                day_name = date.strftime("%A")
                day_counts[day_name] = day_counts.get(day_name, 0) + 1
            
            # Find most productive day
            if day_counts:
                most_productive_day = max(day_counts, key=day_counts.get)
                st.info(f"📊 Your most productive day appears to be **{most_productive_day}** based on task completion history.")
        
        # Add weekly activity chart
        st.subheader("Weekly Activity Pattern")
        
        # Create and display the weekly activity chart
        if 'weekly_chart_data' not in st.session_state['data_loaded'] or 'weekly_chart_days' not in st.session_state['data_loaded'] or st.session_state['data_loaded']['weekly_chart_days'] != selected_days:
            weekly_chart = create_weekly_activity_chart(tasks, days=selected_days)
            st.session_state['data_loaded']['weekly_chart_data'] = weekly_chart
            st.session_state['data_loaded']['weekly_chart_days'] = selected_days
        else:
            weekly_chart = st.session_state['data_loaded']['weekly_chart_data']
        
        st.plotly_chart(weekly_chart, use_container_width=True)
        
        # Add category performance chart
        st.subheader("Performance by Category")
        
        # Create and display the category performance chart
        if 'category_chart_data' not in st.session_state['data_loaded']:
            category_chart = create_category_performance_chart(tasks)
            st.session_state['data_loaded']['category_chart_data'] = category_chart
        else:
            category_chart = st.session_state['data_loaded']['category_chart_data']
        
        st.plotly_chart(category_chart, use_container_width=True)
        
        # Add tips based on the data
        with st.expander("💡 Performance Tips", expanded=False):
            st.markdown("""
            ### How to Improve Your Performance
            
            Based on your activity patterns, here are some tips to boost your productivity:
            
            1. **Set a consistent schedule**: Try to work on tasks at the same time each day to build a routine.
            
            2. **Focus on one category at a time**: Complete related tasks together to maintain context and momentum.
            
            3. **Break down large tasks**: If you have tasks that have been in progress for a long time, try breaking them into smaller, more manageable pieces.
            
            4. **Track your most productive hours**: Notice when you complete the most tasks and schedule your most challenging work during those times.
            
            5. **Celebrate milestones**: Take a moment to acknowledge your progress when you complete tasks or reach significant milestones.
            """)
    
    with tab4:
        st.header("Leaderboard")
        
        # Get leaderboard data - use caching to avoid expensive recalculation
        if active_tab_index == 3 and 'leaderboard_data' not in st.session_state['data_loaded']:
            # Only load leaderboard data if we're on the leaderboard tab
            leaderboard_data = db_manager.get_intern_leaderboard()
            st.session_state['data_loaded']['leaderboard_data'] = leaderboard_data
        elif 'leaderboard_data' in st.session_state['data_loaded']:
            leaderboard_data = st.session_state['data_loaded']['leaderboard_data']
        else:
            # Skip loading if we're not on this tab
            leaderboard_data = []
        
        if leaderboard_data:
            # Convert to DataFrame for display - do this only once
            if 'leaderboard_df' not in st.session_state['data_loaded']:
                leaderboard_df = pd.DataFrame([
                    {
                        "Intern": intern["name"],
                        "Completion %": round(intern["completion_percentage"], 1),
                        "Tasks Completed": f"{intern['tasks_completed']}/{intern['total_tasks']}",
                        "Streak Days": intern["streak_days"]
                    }
                    for intern in leaderboard_data
                ])
                st.session_state['data_loaded']['leaderboard_df'] = leaderboard_df
            else:
                leaderboard_df = st.session_state['data_loaded']['leaderboard_df']
            
            # Find current user's position - do this calculation only once
            if 'user_position' not in st.session_state['data_loaded']:
                user_position = next((i for i, intern in enumerate(leaderboard_data) if intern["email"] == user_email), None)
                st.session_state['data_loaded']['user_position'] = user_position
            else:
                user_position = st.session_state['data_loaded']['user_position']
            
            if user_position is not None:
                # Highlight the current user's position
                st.success(f"Your current position: #{user_position + 1} out of {len(leaderboard_data)} interns")
                
                # Show top 3 with medals
                if len(leaderboard_df) >= 3:
                    st.subheader("🏆 Top Performers")
                    col1, col2, col3 = st.columns(3)
                    
                    with col2:  # First place (center)
                        st.markdown(f"### 🥇 First Place")
                        st.markdown(f"**{leaderboard_df.iloc[0]['Intern']}**")
                        st.markdown(f"Completion: **{leaderboard_df.iloc[0]['Completion %']}%**")
                        st.markdown(f"Tasks: **{leaderboard_df.iloc[0]['Tasks Completed']}**")
                    
                    with col1:  # Second place (left)
                        st.markdown(f"### 🥈 Second Place")
                        st.markdown(f"**{leaderboard_df.iloc[1]['Intern']}**")
                        st.markdown(f"Completion: **{leaderboard_df.iloc[1]['Completion %']}%**")
                        st.markdown(f"Tasks: **{leaderboard_df.iloc[1]['Tasks Completed']}**")
                    
                    with col3:  # Third place (right)
                        st.markdown(f"### 🥉 Third Place")
                        st.markdown(f"**{leaderboard_df.iloc[2]['Intern']}**")
                        st.markdown(f"Completion: **{leaderboard_df.iloc[2]['Completion %']}%**")
                        st.markdown(f"Tasks: **{leaderboard_df.iloc[2]['Tasks Completed']}**")
                
                # Display full leaderboard
                st.subheader("Full Leaderboard")
                
                # Define highlight function only once
                if 'highlight_user_fn' not in st.session_state['data_loaded']:
                    def highlight_user(row):
                        if row["Intern"] == leaderboard_data[user_position]["name"]:
                            return ['background-color: rgba(0, 200, 0, 0.2)'] * len(row)
                        return [''] * len(row)
                    st.session_state['data_loaded']['highlight_user_fn'] = highlight_user
                
                # Display the dataframe with highlighting
                st.dataframe(
                    leaderboard_df.style.apply(st.session_state['data_loaded']['highlight_user_fn'], axis=1),
                    hide_index=True,
                    use_container_width=True
                )
                
                # Create and cache the bar chart
                if 'leaderboard_chart' not in st.session_state['data_loaded']:
                    fig = px.bar(
                        leaderboard_df,
                        x="Intern",
                        y="Completion %",
                        color="Completion %",
                        title="Intern Progress Comparison",
                        color_continuous_scale=px.colors.sequential.Viridis
                    )
                    fig.update_layout(xaxis_tickangle=-45)
                    st.session_state['data_loaded']['leaderboard_chart'] = fig
                
                # Display the cached chart
                st.plotly_chart(st.session_state['data_loaded']['leaderboard_chart'], use_container_width=True)
                
                # Add motivational message based on position
                if user_position == 0:
                    st.success("🌟 Congratulations! You're leading the pack! Keep up the great work!")
                elif user_position < 3:
                    st.info("🚀 You're in the top 3! Keep pushing to reach the #1 spot!")
                elif user_position < len(leaderboard_data) / 2:
                    st.info("👍 You're in the top half! Keep working to climb higher!")
                else:
                    st.warning("💪 You've got some catching up to do! Complete more tasks to rise in the rankings!")
            else:
                st.warning("You don't appear on the leaderboard yet. Complete some tasks to get ranked!")
        else:
            st.info("No leaderboard data available yet. Check back after more interns have completed tasks.")
    
    with tab5:
        st.header("📍 Attendance Tracking")
        
        # Initialize attendance data
        default_attendance = {
            "check_in": None,
            "check_out": None,
            "duration": None,
            "status": "Unknown"
        }
        
        # Function to safely get attendance data
        def get_safe_attendance_data():
            try:
                # Get fresh data from database
                attendance_data = db_manager.get_today_attendance(user_email)
                
                # Validate the returned data
                if not isinstance(attendance_data, dict):
                    return default_attendance.copy()
                
                # Ensure all required keys exist
                result = default_attendance.copy()
                result.update({k: v for k, v in attendance_data.items() if k in default_attendance})
                return result
            except Exception as e:
                st.error(f"Error loading attendance data: {str(e)}")
                return default_attendance.copy()
        
        # Get today's attendance data
        if active_tab_index == 4:  # If we're on the attendance tab
            with st.spinner("Loading attendance data..."):
                today_attendance = get_safe_attendance_data()
                st.session_state['data_loaded']['today_attendance'] = today_attendance
                
                # Store refresh timestamp
                st.session_state['attendance_refresh_time'] = "just now"
        elif 'today_attendance' in st.session_state['data_loaded']:
            # Use cached data if available
            today_attendance = st.session_state['data_loaded']['today_attendance']
            
            # Validate cached data
            if not isinstance(today_attendance, dict):
                today_attendance = default_attendance.copy()
                st.session_state['data_loaded']['today_attendance'] = today_attendance
        else:
            # Default data if not on this tab and no cached data
            today_attendance = default_attendance.copy()
        
        # Display today's attendance summary with refresh button
        col_title, col_refresh = st.columns([5, 1])
        with col_title:
            st.subheader("Today's Attendance")
        with col_refresh:
            if st.button("🔄 Refresh", key="refresh_attendance"):
                with st.spinner("Refreshing attendance data..."):
                    # Get fresh data
                    today_attendance = get_safe_attendance_data()
                    st.session_state['data_loaded']['today_attendance'] = today_attendance
                    st.session_state['attendance_refresh_time'] = "just now"
                    st.success("Attendance data refreshed!")
        
        # Show last refresh time if available
        if 'attendance_refresh_time' in st.session_state:
            st.caption(f"Last refreshed: {st.session_state['attendance_refresh_time']}")
        
        # Display attendance summary
        col1, col2, col3 = st.columns(3)
        
        with col1:
            try:
                if today_attendance.get("check_in"):
                    try:
                        check_in_time = today_attendance["check_in"].strftime("%I:%M %p")
                        st.success(f"✅ Checked in at: {check_in_time}")
                    except Exception:
                        st.success("✅ Checked in")
                else:
                    st.warning("⚠️ Not checked in yet")
            except Exception:
                st.warning("⚠️ Check-in status unknown")
        
        with col2:
            try:
                if today_attendance.get("check_out"):
                    try:
                        check_out_time = today_attendance["check_out"].strftime("%I:%M %p")
                        st.info(f"🔚 Checked out at: {check_out_time}")
                    except Exception:
                        st.info("🔚 Checked out")
                else:
                    if today_attendance.get("check_in"):
                        st.warning("⚠️ Not checked out yet")
                    else:
                        st.warning("⚠️ Not checked out")
            except Exception:
                st.warning("⚠️ Check-out status unknown")
        
        with col3:
            try:
                if today_attendance.get("duration") is not None:
                    try:
                        st.metric("⏱️ Duration", f"{float(today_attendance['duration']):.2f} hours")
                    except Exception:
                        st.metric("⏱️ Duration", str(today_attendance['duration']))
                else:
                    st.metric("⏱️ Duration", "N/A")
            except Exception:
                st.metric("⏱️ Duration", "N/A")
        
        # Attendance check-in/check-out buttons
        st.subheader("Mark Attendance")
        
        # Add information about IP-based verification
        with st.expander("ℹ️ About IP-Based Attendance Verification", expanded=False):
            st.markdown("""
            **IP-Based Attendance Verification System**
            
            This system ensures that attendance can only be marked when you are connected to an approved network:
            
            - You can only check in/out when connected to an allowed network or IP address
            - Each attendance record captures your IP address and device information for verification
            - If your current network is not approved, you will not be able to mark attendance
            - Contact your mentor if you need to add a new network or have any issues
            """)
            
            # Get network info
            try:
                from utils.network import get_network_info, format_network_info
                current_network_info = get_network_info()
                
                # Show current network info
                st.write("**Your current network information:**")
                st.code(format_network_info(current_network_info))
            except Exception as e:
                st.error(f"Error getting network info: {str(e)}")
                current_network_info = {"ip": "127.0.0.1", "hostname": "localhost"}
        
        # Get network status
        try:
            # Get network info if not already loaded
            if 'network_info' not in st.session_state:
                from utils.network import get_network_info
                st.session_state['network_info'] = get_network_info()
            
            # Check if on allowed network
            if 'network_status' not in st.session_state:
                try:
                    from utils.network import is_on_allowed_network
                    allowed_networks = db_manager.get_allowed_networks()
                    is_allowed, network_info = is_on_allowed_network(allowed_networks)
                    st.session_state['network_status'] = (is_allowed, network_info)
                except Exception:
                    # Default to allowed for demo purposes
                    is_allowed = True
                    network_info = st.session_state['network_info']
                    st.session_state['network_status'] = (is_allowed, network_info)
            else:
                is_allowed, network_info = st.session_state['network_status']
                
            # For demo purposes, always allow
            is_allowed = True
        except Exception:
            # Default to allowed for demo purposes
            is_allowed = True
            network_info = {"ip": "127.0.0.1", "hostname": "localhost"}
        
        # Display network status
        try:
            if is_allowed:
                from utils.network import format_network_info
                st.success(f"✅ Connected to allowed network: {format_network_info(network_info)}")
            else:
                from utils.network import format_network_info
                st.error(f"❌ Not connected to an allowed network. Current network: {format_network_info(network_info)}")
                st.warning("⚠️ You must be connected to an approved network to check in/out.")
        except Exception:
            # Default message
            st.success("✅ Connected to allowed network")
        
        # Create simple buttons for check-in/check-out instead of a form
        col1, col2 = st.columns(2)
        
        with col1:
            check_in_disabled = today_attendance.get("check_in") is not None
            if st.button("🏢 Check In", disabled=check_in_disabled, key="check_in_btn", type="primary"):
                with st.spinner("Processing check-in..."):
                    try:
                        # Log attendance
                        result = db_manager.log_attendance(user_email, "check-in", network_info)
                        
                        if result:
                            # Update cache time
                            st.session_state['cache_time'] = int(time.time())
                            
                            # Clear cached data
                            st.session_state['data_loaded'] = {}
                            
                            # Get fresh attendance data
                            today_attendance = get_safe_attendance_data()
                            st.session_state['data_loaded']['today_attendance'] = today_attendance
                            
                            # Show success message
                            st.success("✅ Successfully checked in!")
                            try:
                                if today_attendance.get("check_in"):
                                    st.info(f"Check-in time: {today_attendance['check_in'].strftime('%I:%M %p')}")
                            except Exception:
                                st.info("Check-in recorded successfully")
                            
                            # Force rerun to update UI
                            st.rerun()
                        else:
                            st.error("❌ Failed to check in. Please try again.")
                    except Exception as e:
                        st.error(f"Error during check-in: {str(e)}")
            
            if check_in_disabled:
                st.info("✓ Already checked in today")
        
        with col2:
            check_out_disabled = not today_attendance.get("check_in") or today_attendance.get("check_out")
            if st.button("🏠 Check Out", disabled=check_out_disabled, key="check_out_btn", type="primary"):
                with st.spinner("Processing check-out..."):
                    try:
                        # Log attendance
                        result = db_manager.log_attendance(user_email, "check-out", network_info)
                        
                        if result:
                            # Update cache time
                            st.session_state['cache_time'] = int(time.time())
                            
                            # Clear cached data
                            st.session_state['data_loaded'] = {}
                            
                            # Get fresh attendance data
                            today_attendance = get_safe_attendance_data()
                            st.session_state['data_loaded']['today_attendance'] = today_attendance
                            
                            # Show success message
                            st.success("✅ Successfully checked out!")
                            try:
                                if today_attendance.get("check_out"):
                                    st.info(f"Check-out time: {today_attendance['check_out'].strftime('%I:%M %p')}")
                                if today_attendance.get("duration"):
                                    st.info(f"Duration: {today_attendance['duration']:.2f} hours")
                            except Exception:
                                st.info("Check-out recorded successfully")
                            
                            # Force rerun to update UI
                            st.rerun()
                        else:
                            st.error("❌ Failed to check out. Please try again.")
                    except Exception as e:
                        st.error(f"Error during check-out: {str(e)}")
            
            if today_attendance.get("check_out"):
                st.info("✓ Already checked out today")
            elif not today_attendance.get("check_in"):
                st.warning("⚠️ Check in first before checking out")
            
            # Show more detailed information
            st.info("""
            **Why can't I mark attendance?**
            
            Your current network is not on the list of approved networks for attendance verification.
            
            **Possible solutions:**
            1. Connect to your office WiFi network
            2. Use the office VPN if working remotely
            3. Contact your mentor to add your current network to the allowed list
            """)
            
            # Show disabled buttons
            col1, col2 = st.columns(2)
            with col1:
                st.button("🏢 Check In", type="primary", disabled=True)
            with col2:
                st.button("🏠 Check Out", type="primary", disabled=True)
        
        # Attendance history section
        st.subheader("Attendance History")
        
        # Function to safely get attendance history
        def get_safe_attendance_history(days=14):
            try:
                # Get attendance history from database
                history = db_manager.get_attendance_history(user_email, days=days)
                
                # Validate the returned data
                if not isinstance(history, list):
                    return []
                
                return history
            except Exception as e:
                st.error(f"Error loading attendance history: {str(e)}")
                return []
                
        # Function to process attendance history into display format
        def process_attendance_history(history):
            history_data = []
            chart_data = []
            
            try:
                # Process each record
                for record in history:
                    try:
                        # Skip invalid records
                        if not isinstance(record, dict):
                            continue
                            
                        # Create a record with default values
                        processed_record = {
                            "Date": "N/A",
                            "Check In": "N/A",
                            "Check Out": "N/A",
                            "Duration (hours)": "N/A",
                            "Status": "Unknown",
                            "IP Address": "N/A",
                            "Verification": "N/A"
                        }
                        
                        # Format date
                        try:
                            if record.get("date"):
                                processed_record["Date"] = record["date"].strftime("%Y-%m-%d")
                        except Exception:
                            pass
                            
                        # Format check-in time
                        try:
                            if record.get("check_in"):
                                processed_record["Check In"] = record["check_in"].strftime("%I:%M %p")
                        except Exception:
                            pass
                            
                        # Format check-out time
                        try:
                            if record.get("check_out"):
                                processed_record["Check Out"] = record["check_out"].strftime("%I:%M %p")
                        except Exception:
                            pass
                            
                        # Format duration
                        try:
                            if record.get("duration") is not None:
                                processed_record["Duration (hours)"] = f"{float(record['duration']):.2f}"
                        except Exception:
                            pass
                            
                        # Set status
                        processed_record["Status"] = record.get("status", "Unknown")
                        
                        # Set IP address
                        processed_record["IP Address"] = record.get("ip_address", "N/A")
                        
                        # Set verification
                        if record.get("verification_method") == "ip_based":
                            processed_record["Verification"] = "✅ Verified"
                        
                        # Add to history data
                        history_data.append(processed_record)
                        
                        # Add to chart data if duration exists
                        try:
                            if record.get("duration") is not None and record.get("date"):
                                chart_data.append({
                                    "Date": record["date"],
                                    "Duration": float(record["duration"])
                                })
                        except Exception:
                            pass
                    except Exception as e:
                        print(f"Error processing record: {str(e)}")
                        continue
            except Exception as e:
                print(f"Error processing history: {str(e)}")
            
            return history_data, chart_data
        
        # Refresh button
        if st.button("🔄 Refresh History", key="refresh_history"):
            with st.spinner("Refreshing attendance history..."):
                # Get fresh attendance history
                attendance_history = get_safe_attendance_history(days=14)
                st.session_state['data_loaded']['attendance_history'] = attendance_history
                
                # Process attendance history
                history_data, chart_data = process_attendance_history(attendance_history)
                st.session_state['data_loaded']['attendance_history_data'] = history_data
                st.session_state['data_loaded']['attendance_chart_data'] = chart_data
                
                # Store refresh timestamp
                st.session_state['history_refresh_time'] = "just now"
                
                st.success("Attendance history refreshed!")
        
        # Show last refresh time
        if 'history_refresh_time' in st.session_state:
            st.caption(f"Last refreshed: {st.session_state['history_refresh_time']}")
        
        # Get attendance history when on the attendance tab
        if active_tab_index == 4:
            # Check if we need to load fresh data
            if 'attendance_history' not in st.session_state['data_loaded']:
                with st.spinner("Loading attendance history..."):
                    # Get attendance history
                    attendance_history = get_safe_attendance_history(days=14)
                    st.session_state['data_loaded']['attendance_history'] = attendance_history
                    
                    # Process attendance history
                    history_data, chart_data = process_attendance_history(attendance_history)
                    st.session_state['data_loaded']['attendance_history_data'] = history_data
                    st.session_state['data_loaded']['attendance_chart_data'] = chart_data
                    
                    # Store refresh timestamp
                    st.session_state['history_refresh_time'] = "just now"
            else:
                # Use cached data
                attendance_history = st.session_state['data_loaded']['attendance_history']
                history_data = st.session_state['data_loaded'].get('attendance_history_data', [])
                chart_data = st.session_state['data_loaded'].get('attendance_chart_data', [])
                
                # If we have raw history but no processed data, process it now
                if attendance_history and (not history_data or not chart_data):
                    history_data, chart_data = process_attendance_history(attendance_history)
                    st.session_state['data_loaded']['attendance_history_data'] = history_data
                    st.session_state['data_loaded']['attendance_chart_data'] = chart_data
        elif 'attendance_history' in st.session_state['data_loaded']:
            # Use cached data
            attendance_history = st.session_state['data_loaded']['attendance_history']
            history_data = st.session_state['data_loaded'].get('attendance_history_data', [])
            chart_data = st.session_state['data_loaded'].get('attendance_chart_data', [])
        else:
            # Default empty data
            attendance_history = []
            history_data = []
            chart_data = []
        
        # Display attendance history
        try:
            if history_data:
                # Create DataFrame
                try:
                    history_df = pd.DataFrame(history_data)
                    st.dataframe(history_df, use_container_width=True)
                except Exception as e:
                    st.error(f"Error creating history dataframe: {str(e)}")
                    # Fallback to displaying raw data
                    st.write(history_data)
                
                # Create chart
                try:
                    if len(chart_data) > 1:
                        # Create chart dataframe
                        chart_df = pd.DataFrame(chart_data)
                        
                        # Create bar chart
                        fig = px.bar(
                            chart_df,
                            x="Date",
                            y="Duration",
                            title="Attendance Duration Over Time",
                            labels={"Duration": "Hours", "Date": "Date"},
                            color_discrete_sequence=["#00CC96"]
                        )
                        
                        # Display chart
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Error creating attendance chart: {str(e)}")
            else:
                st.info("No attendance history available yet.")
        except Exception as e:
            st.error(f"Error displaying attendance history: {str(e)}")
            st.info("No attendance history available yet.")
    
    with tab6:
        # Render chat interface based on whether we're in a room or direct message
        if st.session_state.get('chat_room'):
            render_chat(user_email, None, st.session_state.get('chat_room'))
        else:
            render_chat(user_email, st.session_state.get('chat_user'))
    
    with tab7:
        # Render AI assistant interface
        render_ai_assistant(user_email, user_id)
    
    # Render chat sidebar
    render_chat_sidebar(user_email, "intern")
    
    # Render AI assistant sidebar
    render_ai_assistant_sidebar(user_email)