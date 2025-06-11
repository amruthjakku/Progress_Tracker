import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from models.database import DatabaseManager

def render_meetings_dashboard(user_email):
    """
    Render a dashboard for managing video/audio meetings
    
    Args:
        user_email (str): The user's email
    """
    st.header("📹 Video Meetings")
    st.caption("Create and manage video meetings using virtual.swecha.org")
    
    # Initialize database manager
    db = DatabaseManager()
    
    # Create tabs for different sections
    tab1, tab2 = st.tabs(["Active Meetings", "Create New Meeting"])
    
    with tab1:
        # Get all recent meetings
        recent_meetings = db.get_recent_meetings(limit=50)
        
        if recent_meetings:
            # Convert to DataFrame for easier display
            meetings_data = []
            for meeting in recent_meetings:
                meetings_data.append({
                    "Room": meeting.get("room_name", "Unknown"),
                    "Created By": db.get_user_name(meeting.get("created_by", "Unknown")),
                    "Created At": meeting.get("created_at", datetime.now()).strftime("%Y-%m-%d %I:%M %p"),
                    "Link": meeting.get("meeting_link", "#"),
                    "ID": str(meeting.get("_id", ""))
                })
            
            meetings_df = pd.DataFrame(meetings_data)
            
            # Display meetings in a table
            st.dataframe(
                meetings_df[["Room", "Created By", "Created At"]],
                hide_index=True,
                use_container_width=True
            )
            
            # Allow joining a selected meeting
            selected_meeting = st.selectbox(
                "Select a meeting to join",
                options=meetings_df["ID"].tolist(),
                format_func=lambda x: f"{meetings_df[meetings_df['ID'] == x]['Room'].iloc[0]} - {meetings_df[meetings_df['ID'] == x]['Created At'].iloc[0]}"
            )
            
            if selected_meeting:
                meeting_link = meetings_df[meetings_df["ID"] == selected_meeting]["Link"].iloc[0]
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("🎥 Join Meeting", key=f"join_btn_{selected_meeting}", use_container_width=True):
                        st.markdown(f'<script>window.open("{meeting_link}", "_blank");</script>', unsafe_allow_html=True)
                        st.success(f"Opening meeting...")
                with col2:
                    st.code(meeting_link, language=None)
        else:
            st.info("No recent meetings found. Create a new meeting to get started.")
    
    with tab2:
        st.subheader("Create a New Meeting")
        
        # Form for creating a new meeting
        with st.form("create_meeting_form"):
            # Meeting room name
            room_name = st.text_input(
                "Meeting Room Name",
                help="Enter a descriptive name for the meeting room"
            )
            
            # Meeting type selection
            meeting_type = st.radio(
                "Meeting Type",
                options=["Task Discussion", "Project Review", "General", "Custom"],
                horizontal=True
            )
            
            # Custom room name if selected
            custom_room = st.text_input(
                "Custom Room Name",
                disabled=(meeting_type != "Custom"),
                help="Enter a custom room name if you selected 'Custom'"
            )
            
            # Participants selection
            interns = db.get_users_by_role("intern")
            intern_options = [i["email"] for i in interns]
            
            selected_participants = st.multiselect(
                "Select Participants",
                options=intern_options,
                format_func=lambda x: db.get_user_name(x),
                help="Select the interns who should join this meeting"
            )
            
            # Submit button
            submitted = st.form_submit_button("Create Meeting")
            
            if submitted:
                if room_name or (meeting_type == "Custom" and custom_room):
                    # Generate the room name based on selection
                    if meeting_type == "Custom" and custom_room:
                        final_room_name = custom_room.replace(" ", "-").lower()
                    else:
                        final_room_name = f"{meeting_type.lower()}-{room_name.replace(' ', '-').lower()}"
                    
                    # Generate meeting link
                    meeting_link = f"https://virtual.swecha.org/room/{final_room_name}"
                    
                    # Log the meeting
                    meeting_id = db.log_meeting(final_room_name, meeting_link, user_email)
                    
                    if meeting_id:
                        st.success(f"Meeting created successfully!")
                        
                        # Display meeting information
                        st.subheader("Meeting Information")
                        st.write(f"**Room Name:** {final_room_name}")
                        st.write(f"**Meeting Link:**")
                        st.code(meeting_link, language=None)
                        
                        # Join button outside the form
                        if st.button("🎥 Join Meeting Now", key="join_new_meeting_btn"):
                            st.markdown(f'<script>window.open("{meeting_link}", "_blank");</script>', unsafe_allow_html=True)
                            
                        # Share with participants
                        if selected_participants:
                            st.write("**Share with participants:**")
                            
                            # Create a message to share
                            share_message = f"""
                            I've created a new meeting: {final_room_name}
                            
                            Join using this link: {meeting_link}
                            """
                            
                            # Option to send message to selected participants
                            if st.button("📨 Notify Selected Participants", key="notify_participants_btn"):
                                for participant in selected_participants:
                                    try:
                                        # Save a direct message to each participant
                                        db.save_chat_message(
                                            sender_email=user_email,
                                            message=share_message,
                                            recipient_email=participant
                                        )
                                    except Exception as e:
                                        st.error(f"Error notifying {participant}: {str(e)}")
                                
                                st.success(f"Notifications sent to {len(selected_participants)} participants!")
                    else:
                        st.error("Error creating meeting. Please try again.")
                else:
                    st.error("Please provide a meeting room name.")
    
    # Display meeting statistics
    st.subheader("Meeting Statistics")
    
    try:
        # Get all meetings
        all_meetings = list(db.db.meetings.find())
        
        # Calculate statistics
        total_meetings = len(all_meetings)
        
        # Meetings by day
        today = datetime.now().date()
        meetings_today = sum(1 for m in all_meetings if m.get("created_at", datetime.now()).date() == today)
        
        # Meetings by room
        room_counts = {}
        for meeting in all_meetings:
            room_name = meeting.get("room_name", "Unknown")
            room_counts[room_name] = room_counts.get(room_name, 0) + 1
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Meetings", total_meetings)
        with col2:
            st.metric("Meetings Today", meetings_today)
        with col3:
            most_popular_room = max(room_counts.items(), key=lambda x: x[1])[0] if room_counts else "None"
            st.metric("Most Popular Room", most_popular_room)
        
        # Display room statistics
        if room_counts:
            room_data = [{"Room": room, "Count": count} for room, count in room_counts.items()]
            room_df = pd.DataFrame(room_data).sort_values(by="Count", ascending=False)
            
            st.subheader("Meetings by Room")
            st.bar_chart(room_df.set_index("Room"))
    except Exception as e:
        st.error(f"Error calculating meeting statistics: {str(e)}")

def render_meetings_sidebar(user_email):
    """Render a sidebar widget for quick access to meetings"""
    db = DatabaseManager()
    
    with st.sidebar:
        st.write("### 📹 Meetings")
        
        # Get recent meetings
        recent_meetings = db.get_recent_meetings(limit=3)
        
        if recent_meetings:
            st.caption("Recent meetings:")
            
            for meeting in recent_meetings:
                room_name = meeting.get("room_name", "Unknown")
                meeting_link = meeting.get("meeting_link", "#")
                
                if st.button(f"🎥 {room_name}", key=f"sidebar_meeting_{str(meeting.get('_id', ''))}"):
                    st.markdown(f'<script>window.open("{meeting_link}", "_blank");</script>', unsafe_allow_html=True)
                    st.success(f"Opening meeting...")
        
        # Quick create meeting
        st.caption("Quick create:")
        
        quick_room = st.text_input("Room name", key="sidebar_quick_room")
        
        if st.button("Create & Join", key="sidebar_create_meeting_btn"):
            if quick_room:
                room_name = quick_room.replace(" ", "-").lower()
                meeting_link = f"https://virtual.swecha.org/room/{room_name}"
                
                # Log the meeting
                db.log_meeting(room_name, meeting_link, user_email)
                
                # Open the meeting
                st.markdown(f'<script>window.open("{meeting_link}", "_blank");</script>', unsafe_allow_html=True)
                st.success(f"Meeting created! Opening {meeting_link}")
            else:
                st.error("Please enter a room name.")