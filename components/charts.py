import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime, timedelta

def create_progress_chart(progress_data, title="Progress Overview"):
    """Create a progress bar chart"""
    fig = px.bar(
        progress_data,
        x="Task",
        y="Progress",
        color="Status",
        title=title,
        labels={"Progress": "Completion %", "Task": "Task Name"},
        color_discrete_map={"Done": "#00CC96", "In Progress": "#636EFA", "Not Started": "#EF553B"}
    )
    return fig

def create_activity_timeline(activities, title="Activity Timeline"):
    """Create an activity timeline chart"""
    fig = px.timeline(
        activities,
        x_start="Start",
        x_end="End",
        y="Task",
        color="Status",
        title=title,
        color_discrete_map={"Done": "#00CC96", "In Progress": "#636EFA", "Not Started": "#EF553B"}
    )
    fig.update_layout(showlegend=True)
    return fig

def create_progress_stats(total, completed):
    """Create progress statistics with metrics"""
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Tasks", total)
    with col2:
        st.metric("Completed", completed)
    with col3:
        percentage = (completed / total * 100) if total > 0 else 0
        st.metric("Progress", f"{percentage:.1f}%")
    
    # Progress bar
    st.progress(percentage / 100, text=f"Overall Progress: {percentage:.1f}%")

def render_charts():
    st.write("### Progress Charts")
    # This function is kept for backward compatibility
    pass