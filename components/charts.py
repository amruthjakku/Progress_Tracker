import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta
import networkx as nx

def create_progress_chart(progress_data, title="Progress Overview"):
    """Create a progress bar chart with hover information"""
    fig = px.bar(
        progress_data,
        x="Task",
        y="Progress",
        color="Status",
        title=title,
        labels={"Progress": "Completion %", "Task": "Task Name"},
        color_discrete_map={
            "Done": "#00CC96",
            "In Progress": "#636EFA",
            "Not Started": "#EF553B"
        },
        hover_data=["Time Spent"]
    )
    fig.update_layout(showlegend=True)
    return fig

def create_activity_timeline(activities, title="Activity Timeline"):
    """Create an activity timeline with hover information"""
    fig = px.timeline(
        activities,
        x_start="Start",
        x_end="End",
        y="Task",
        color="Status",
        title=title,
        hover_data=["Time Spent", "Submission"],
        color_discrete_map={
            "Done": "#00CC96",
            "In Progress": "#636EFA",
            "Not Started": "#EF553B"
        }
    )
    fig.update_layout(showlegend=True)
    return fig

def create_dependency_graph(tasks, get_dependencies_func):
    """
    Create an enhanced interactive task dependency graph with improved layout,
    hover information, and visual indicators for task relationships.
    
    Args:
        tasks: List of task objects
        get_dependencies_func: Function to get task dependencies
    """
    G = nx.DiGraph()
    
    # Store task details for hover information
    task_details = {}
    
    # Create a lookup dictionary for tasks by ID
    tasks_by_id = {str(task["_id"]): task for task in tasks}
    
    # First pass: Add all nodes
    for task in tasks:
        task_id = str(task["_id"])
        task_title = task["title"]
        
        # Determine task status
        if isinstance(task.get("progress"), list):
            # Handle case where progress is a list of progress records
            progress_statuses = [p.get("status") for p in task.get("progress", []) if p.get("status")]
            if "done" in progress_statuses:
                task_status = "done"
            elif "in_progress" in progress_statuses:
                task_status = "in_progress"
            else:
                task_status = "not_started"
        else:
            # Handle case where progress is a single object
            task_status = task.get("progress", {}).get("status", "not_started")
        
        task_category = task.get("category", "Uncategorized")
        task_description = task.get("description", "")
        
        # Store task details for hover information
        task_details[task_title] = {
            "id": task_id,
            "status": task_status,
            "category": task_category,
            "description": task_description[:100] + "..." if len(task_description) > 100 else task_description
        }
        
        # Add node with metadata
        G.add_node(
            task_title, 
            status=task_status,
            category=task_category,
            id=task_id
        )
    
    # Second pass: Add all edges using the task_dependencies collection
    for task in tasks:
        task_id = str(task["_id"])
        task_title = task["title"]
        
        # Get dependencies for this task
        dependencies = get_dependencies_func(task_id)
        
        # Add edges for prerequisites
        for prereq_title, status in dependencies.items():
            # Find the prerequisite task by title
            prereq_task = next((t for t in tasks if t["title"] == prereq_title), None)
            if prereq_task:
                G.add_edge(prereq_title, task_title)
    
    # Use a hierarchical layout for better visualization of dependencies
    try:
        # Try to use a hierarchical layout first
        pos = nx.nx_pydot.graphviz_layout(G, prog="dot")
    except:
        # Fall back to spring layout if graphviz is not available
        pos = nx.spring_layout(G, k=0.5, iterations=50)
    
    # Create edge traces with arrows
    edge_x = []
    edge_y = []
    edge_text = []
    
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        
        # Calculate arrow position (80% along the edge)
        arrow_x = x0 + 0.8 * (x1 - x0)
        arrow_y = y0 + 0.8 * (y1 - y0)
        
        # Add the main edge
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
        edge_text.append(f"{edge[0]} → {edge[1]}")
    
    edge_trace = go.Scatter(
        x=edge_x, 
        y=edge_y,
        line=dict(width=1.5, color="#888"),
        hoverinfo="text",
        text=edge_text,
        mode="lines",
        name="Dependencies"
    )
    
    # Create node traces for each status with enhanced styling
    status_colors = {
        "done": "#00CC96",
        "in_progress": "#636EFA",
        "not_started": "#EF553B"
    }
    
    status_symbols = {
        "done": "star",  # Using a star for completed tasks
        "in_progress": "circle-dot",  # Using a dotted circle for in-progress tasks
        "not_started": "circle"  # Using a plain circle for not started tasks
    }
    
    node_traces = {}
    for status in status_colors:
        node_traces[status] = go.Scatter(
            x=[],
            y=[],
            mode="markers+text",
            name=status.replace("_", " ").title(),
            text=[],
            hoverinfo="text",
            hovertext=[],
            marker=dict(
                size=25,
                color=status_colors[status],
                line=dict(width=2, color="white"),
                symbol=status_symbols.get(status, "circle")
            ),
            textposition="bottom center"
        )
    
    # Group nodes by category for better visualization
    categories = set(G.nodes[node]["category"] for node in G.nodes())
    category_offsets = {cat: idx * 0.1 for idx, cat in enumerate(categories)}
    
    # Add nodes with enhanced hover information
    for node in G.nodes():
        x, y = pos[node]
        
        # Apply small offset based on category for visual grouping
        category = G.nodes[node]["category"]
        offset = category_offsets.get(category, 0)
        x += offset
        
        status = G.nodes[node]["status"]
        trace = node_traces[status]
        
        # Add node position
        trace["x"] += (x,)
        trace["y"] += (y,)
        
        # Add node label (shortened if too long)
        node_label = node if len(node) < 20 else node[:17] + "..."
        trace["text"] += (node_label,)
        
        # Create rich hover information
        details = task_details.get(node, {})
        hover_text = f"<b>{node}</b><br>"
        hover_text += f"Status: {status.replace('_', ' ').title()}<br>"
        hover_text += f"Category: {details.get('category', 'Unknown')}<br>"
        
        # Add prerequisites and dependents
        prereqs = [pred for pred in G.predecessors(node)]
        dependents = [succ for succ in G.successors(node)]
        
        if prereqs:
            hover_text += f"<br>Prerequisites ({len(prereqs)}):<br>"
            for i, prereq in enumerate(prereqs[:3]):
                hover_text += f"- {prereq}<br>"
            if len(prereqs) > 3:
                hover_text += f"- and {len(prereqs) - 3} more...<br>"
        
        if dependents:
            hover_text += f"<br>Unlocks ({len(dependents)}):<br>"
            for i, dep in enumerate(dependents[:3]):
                hover_text += f"- {dep}<br>"
            if len(dependents) > 3:
                hover_text += f"- and {len(dependents) - 3} more...<br>"
        
        trace["hovertext"] += (hover_text,)
    
    # Create figure with enhanced layout
    fig = go.Figure(
        data=[edge_trace] + list(node_traces.values()),
        layout=go.Layout(
            title={
                "text": "Task Dependencies & Progression Path",
                "y": 0.95,
                "x": 0.5,
                "xanchor": "center",
                "yanchor": "top",
                "font": {"size": 20}
            },
            showlegend=True,
            legend={"title": "Task Status"},
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="#f8f9fa",
            height=600,
            annotations=[
                dict(
                    text="Hover over tasks to see details and relationships",
                    showarrow=False,
                    xref="paper", yref="paper",
                    x=0.01, y=0.01,
                    font=dict(size=12, color="gray")
                )
            ]
        )
    )
    
    # Add buttons for different layouts
    fig.update_layout(
        updatemenus=[
            dict(
                type="buttons",
                direction="right",
                buttons=[
                    dict(
                        args=[{"visible": [True] + [True for _ in node_traces.values()]}],
                        label="Show All",
                        method="update"
                    ),
                    dict(
                        args=[{"visible": [True, True, False, False]}],
                        label="In Progress",
                        method="update"
                    ),
                    dict(
                        args=[{"visible": [True, False, True, False]}],
                        label="Completed",
                        method="update"
                    ),
                    dict(
                        args=[{"visible": [True, False, False, True]}],
                        label="Not Started",
                        method="update"
                    )
                ],
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.5,
                xanchor="center",
                y=1.1,
                yanchor="top"
            )
        ]
    )
    
    return fig

def create_performance_metrics(metrics):
    """Create performance metrics visualization"""
    fig = go.Figure()
    
    # Add completion rate gauge
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=metrics.get("completion_rate", 0),
        domain={"x": [0, 0.5], "y": [0, 0.5]},
        title={"text": "Completion Rate"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#00CC96"},
            "steps": [
                {"range": [0, 30], "color": "#EF553B"},
                {"range": [30, 70], "color": "#636EFA"},
                {"range": [70, 100], "color": "#00CC96"}
            ]
        }
    ))
    
    # Add productivity score gauge
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=metrics.get("productivity_score", 0),
        domain={"x": [0.5, 1], "y": [0, 0.5]},
        title={"text": "Productivity Score"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": "#00CC96"},
            "steps": [
                {"range": [0, 30], "color": "#EF553B"},
                {"range": [30, 70], "color": "#636EFA"},
                {"range": [70, 100], "color": "#00CC96"}
            ]
        }
    ))
    
    # Add streak indicator
    fig.add_trace(go.Indicator(
        mode="number+delta",
        value=metrics.get("streak_days", 0),
        domain={"x": [0, 0.5], "y": [0.6, 1]},
        title={"text": "Current Streak (days)"},
        delta={"reference": metrics.get("previous_streak", 0)}
    ))
    
    # Add tasks completed indicator
    fig.add_trace(go.Indicator(
        mode="number+delta",
        value=metrics.get("tasks_completed", 0),
        domain={"x": [0.5, 1], "y": [0.6, 1]},
        title={"text": "Tasks Completed (this week)"},
        delta={"reference": metrics.get("previous_tasks_completed", 0)}
    ))
    
    fig.update_layout(
        grid={"rows": 2, "columns": 2, "pattern": "independent"},
        height=500
    )
    
    return fig

def create_performance_heatmap(tasks, days=30):
    """
    Create a heatmap visualization of task activity over time
    
    Args:
        tasks: List of task objects with progress information
        days: Number of days to include in the heatmap
    
    Returns:
        Plotly figure object
    """
    # Create date range for the heatmap
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    date_range = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days + 1)]
    
    # Create categories for the heatmap (task statuses)
    categories = ["Started", "Completed", "Submission"]
    
    # Initialize data structure for the heatmap
    heatmap_data = {
        "Date": [],
        "Activity": [],
        "Count": []
    }
    
    # Process tasks to extract activity data
    activity_by_date = {date: {cat: 0 for cat in categories} for date in date_range}
    
    for task in tasks:
        progress = task.get("progress", {})
        
        # Check if task was started
        if progress.get("started_at") and progress.get("started_at").date() >= start_date:
            date_str = progress.get("started_at").strftime("%Y-%m-%d")
            if date_str in activity_by_date:
                activity_by_date[date_str]["Started"] += 1
        
        # Check if task was completed
        if progress.get("completed_at") and progress.get("completed_at").date() >= start_date:
            date_str = progress.get("completed_at").strftime("%Y-%m-%d")
            if date_str in activity_by_date:
                activity_by_date[date_str]["Completed"] += 1
        
        # Check if submission was made
        if progress.get("submission_link") and progress.get("updated_at") and progress.get("updated_at").date() >= start_date:
            date_str = progress.get("updated_at").strftime("%Y-%m-%d")
            if date_str in activity_by_date:
                activity_by_date[date_str]["Submission"] += 1
    
    # Convert to format needed for heatmap
    for date in date_range:
        for category in categories:
            heatmap_data["Date"].append(date)
            heatmap_data["Activity"].append(category)
            heatmap_data["Count"].append(activity_by_date[date][category])
    
    # Create DataFrame
    df = pd.DataFrame(heatmap_data)
    
    # Pivot the DataFrame for the heatmap
    pivot_df = df.pivot(index="Activity", columns="Date", values="Count")
    
    # Create the heatmap
    fig = px.imshow(
        pivot_df,
        labels=dict(x="Date", y="Activity", color="Count"),
        x=pivot_df.columns,
        y=pivot_df.index,
        color_continuous_scale="Viridis",
        title="Task Activity Heatmap"
    )
    
    # Customize layout
    fig.update_layout(
        xaxis=dict(
            tickangle=-45,
            tickmode='array',
            tickvals=list(range(0, len(date_range), 5)),  # Show every 5th date
            ticktext=[date_range[i] for i in range(0, len(date_range), 5)]
        ),
        height=300,
        margin=dict(l=50, r=50, t=80, b=80)
    )
    
    # Add hover information
    fig.update_traces(
        hovertemplate="<b>Date:</b> %{x}<br><b>Activity:</b> %{y}<br><b>Count:</b> %{z}<extra></extra>"
    )
    
    return fig

def create_weekly_activity_chart(tasks, days=30):
    """
    Create a chart showing activity patterns by day of week
    
    Args:
        tasks: List of task objects with progress information
        days: Number of days to look back
        
    Returns:
        Plotly figure object
    """
    # Define the date range
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    
    # Initialize data structure for day of week analysis
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    activity_by_day = {day: {"Started": 0, "Completed": 0, "Submission": 0} for day in days_of_week}
    
    # Process tasks to extract activity data
    for task in tasks:
        progress = task.get("progress", {})
        
        # Check if task was started
        if progress.get("started_at") and progress.get("started_at").date() >= start_date:
            day = progress.get("started_at").strftime("%A")
            activity_by_day[day]["Started"] += 1
        
        # Check if task was completed
        if progress.get("completed_at") and progress.get("completed_at").date() >= start_date:
            day = progress.get("completed_at").strftime("%A")
            activity_by_day[day]["Completed"] += 1
        
        # Check if submission was made
        if progress.get("submission_link") and progress.get("updated_at") and progress.get("updated_at").date() >= start_date:
            day = progress.get("updated_at").strftime("%A")
            activity_by_day[day]["Submission"] += 1
    
    # Convert to format needed for chart
    chart_data = []
    for day in days_of_week:
        for activity, count in activity_by_day[day].items():
            chart_data.append({
                "Day": day,
                "Activity": activity,
                "Count": count
            })
    
    # Create DataFrame
    df = pd.DataFrame(chart_data)
    
    # Create the bar chart
    fig = px.bar(
        df,
        x="Day",
        y="Count",
        color="Activity",
        title="Weekly Activity Pattern",
        labels={"Count": "Number of Tasks", "Day": "Day of Week"},
        color_discrete_map={
            "Started": "#636EFA",
            "Completed": "#00CC96",
            "Submission": "#EF553B"
        },
        barmode="group"
    )
    
    # Customize layout
    fig.update_layout(
        xaxis=dict(categoryorder="array", categoryarray=days_of_week),
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def create_category_performance_chart(tasks):
    """
    Create a chart showing performance by task category
    
    Args:
        tasks: List of task objects with progress information
        
    Returns:
        Plotly figure object
    """
    # Group tasks by category
    categories = {}
    for task in tasks:
        category = task.get("category", "Uncategorized")
        status = task.get("progress", {}).get("status", "not_started")
        
        if category not in categories:
            categories[category] = {"done": 0, "in_progress": 0, "not_started": 0, "total": 0}
        
        categories[category][status] += 1
        categories[category]["total"] += 1
    
    # Convert to format needed for chart
    chart_data = []
    for category, counts in categories.items():
        if counts["total"] > 0:
            completion_rate = (counts["done"] / counts["total"]) * 100
            chart_data.append({
                "Category": category,
                "Completion Rate": completion_rate,
                "Completed": counts["done"],
                "In Progress": counts["in_progress"],
                "Not Started": counts["not_started"],
                "Total": counts["total"]
            })
    
    # Sort by completion rate
    chart_data.sort(key=lambda x: x["Completion Rate"], reverse=True)
    
    # Create DataFrame
    df = pd.DataFrame(chart_data)
    
    # Create the bar chart
    fig = px.bar(
        df,
        x="Category",
        y="Completion Rate",
        title="Performance by Category",
        labels={"Completion Rate": "Completion Rate (%)", "Category": "Task Category"},
        color="Completion Rate",
        color_continuous_scale="Viridis",
        hover_data=["Completed", "In Progress", "Not Started", "Total"]
    )
    
    # Customize layout
    fig.update_layout(
        height=350,
        xaxis_tickangle=-45
    )
    
    return fig

def create_progress_stats(total, completed):
    """Create progress statistics with metrics and streak"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Tasks", total)
    with col2:
        st.metric("Completed", completed)
    with col3:
        percentage = (completed / total * 100) if total > 0 else 0
        st.metric("Progress", f"{percentage:.1f}%")
    with col4:
        st.metric("Current Streak", f"{completed} days")
    
    # Progress bar with custom styling
    st.progress(percentage / 100, text=f"Overall Progress: {percentage:.1f}%")

def render_charts():
    st.write("### Progress Charts")
    # This function is kept for backward compatibility
    pass