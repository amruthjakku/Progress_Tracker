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

def create_dependency_graph(tasks, dependencies):
    """Create an interactive task dependency graph"""
    G = nx.DiGraph()
    
    # Add nodes and edges
    for task in tasks:
        G.add_node(task["title"], status=task.get("progress", {}).get("status", "not_started"))
        for prereq in task.get("prerequisites", []):
            prereq_task = next((t for t in tasks if str(t["_id"]) == prereq), None)
            if prereq_task:
                G.add_edge(prereq_task["title"], task["title"])
    
    # Create positions for the graph
    pos = nx.spring_layout(G)
    
    # Create figure
    edge_trace = go.Scatter(
        x=[], y=[], line=dict(width=0.5, color="#888"), mode="lines"
    )
    
    # Add edges
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_trace["x"] += (x0, x1, None)
        edge_trace["y"] += (y0, y1, None)
    
    # Create node traces for each status
    status_colors = {
        "done": "#00CC96",
        "in_progress": "#636EFA",
        "not_started": "#EF553B"
    }
    
    node_traces = {}
    for status in status_colors:
        node_traces[status] = go.Scatter(
            x=[], y=[],
            mode="markers+text",
            name=status.replace("_", " ").title(),
            text=[],
            marker=dict(
                size=20,
                color=status_colors[status]
            ),
            textposition="bottom center"
        )
    
    # Add nodes
    for node in G.nodes():
        x, y = pos[node]
        status = G.nodes[node]["status"]
        trace = node_traces[status]
        trace["x"] += (x,)
        trace["y"] += (y,)
        trace["text"] += (node,)
    
    # Create figure
    fig = go.Figure(
        data=[edge_trace] + list(node_traces.values()),
        layout=go.Layout(
            title="Task Dependencies",
            showlegend=True,
            hovermode="closest",
            margin=dict(b=0, l=0, r=0, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
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