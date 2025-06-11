import streamlit as st
from datetime import datetime
from models.database import DatabaseManager

def render_chat(user_email: str, other_user: str = None, room: str = None):
    """
    Render chat component that can be used in both intern and mentor dashboards
    If other_user is None and room is None, it shows a general chat room
    If room is specified, it shows a specific room category
    """
    # For debugging only - comment out in production
    # st.write(f"render_chat called with: user_email={user_email}, other_user={other_user}, room={room}")
    
    db = DatabaseManager()
    
    # Initialize chat state if not exists
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    
    # Chat container with user/room info
    if other_user:
        st.write(f"### 💬 Chat with {db.get_user_name(other_user)}")
        # Mark messages from other user as read
        db.mark_messages_read(user_email, other_user)
        
        # Add video call button for direct messages
        col1, col2 = st.columns([3, 1])
        with col2:
            meeting_link = f"https://virtual.swecha.org/room/direct-{user_email.split('@')[0]}-{other_user.split('@')[0]}"
            if st.button("🎥 Video Call", key=f"video_call_{user_email}_{other_user}", use_container_width=True):
                # Log the meeting
                db.log_meeting(f"direct-{user_email}-{other_user}", meeting_link, user_email)
                # Open the meeting link in a new tab
                st.markdown(f'<script>window.open("{meeting_link}", "_blank");</script>', unsafe_allow_html=True)
                st.success(f"Meeting created! Opening {meeting_link}")
            
    elif room:
        # Get room purpose for display
        rooms = db.get_chat_rooms()
        room_info = next((r for r in rooms if r.get("name", "") == room), None)
        room_purpose = room_info.get("purpose", "") if room_info else ""
        
        # Display room name and purpose with video meeting button
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"### 💬 #{room}")
            if room_purpose:
                st.caption(f"{room_purpose}")
        with col2:
            # Create a standardized room link based on the room name
            meeting_link = f"https://virtual.swecha.org/room/{room.replace(' ', '-')}"
            if st.button("🎥 Join Meeting", key=f"join_meeting_{room}", use_container_width=True):
                # Log the meeting
                db.log_meeting(room, meeting_link, user_email)
                # Open the meeting link in a new tab
                st.markdown(f'<script>window.open("{meeting_link}", "_blank");</script>', unsafe_allow_html=True)
                st.success(f"Meeting created! Opening {meeting_link}")
            
    else:
        # General chat room with video meeting option
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write("### 💬 General Chat Room")
        with col2:
            meeting_link = "https://virtual.swecha.org/room/progress-tracker-general"
            if st.button("🎥 Join Meeting", key="join_general_meeting", use_container_width=True):
                # Log the meeting
                db.log_meeting("general", meeting_link, user_email)
                # Open the meeting link in a new tab
                st.markdown(f'<script>window.open("{meeting_link}", "_blank");</script>', unsafe_allow_html=True)
                st.success(f"Meeting created! Opening {meeting_link}")
    
    # Chat messages container with custom styling
    chat_container = st.container()
    with chat_container:
        # Get messages from database based on context
        if room:
            messages = db.get_room_chat_messages(room)
        else:
            messages = db.get_chat_messages(user_email, other_user)
        
        # Display messages
        for msg in messages:
            with st.chat_message(msg["sender_email"]):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{msg['sender_name']}**")
                    st.write(msg["message"])
                with col2:
                    st.caption(msg["timestamp"].strftime("%I:%M %p"))
    
    # Message input area with typing indicator
    message = st.chat_input("Type a message...")
    if message:
        with st.spinner("Sending message..."):
            # Save message to database based on context
            if room:
                db.save_room_chat_message(
                    sender_email=user_email,
                    message=message,
                    room_name=room
                )
            else:
                db.save_chat_message(
                    sender_email=user_email,
                    message=message,
                    recipient_email=other_user
                )
            
            # Add a small delay for better UX
            import time
            time.sleep(0.5)
            
            # Force a rerun to show the new message
            st.rerun()

def render_chat_sidebar(user_email: str, role: str):
    """Render chat sidebar with user list, room categories, and unread message indicators"""
    db = DatabaseManager()
    
    with st.sidebar:
        st.write("### 💬 Chat")
        
        # Create tabs for Direct Messages, Rooms, and Meetings
        dm_tab, rooms_tab, meetings_tab = st.tabs(["Direct Messages", "Rooms", "Meetings"])
        
        with dm_tab:
            if role == "intern":
                # Show mentors list with unread indicators
                mentors = db.get_users_by_role("mentor")
                if mentors:
                    # Get unread messages for each mentor
                    for mentor in mentors:
                        messages = db.get_chat_messages(user_email, mentor["email"])
                        unread = sum(1 for m in messages 
                                   if m["sender_email"] == mentor["email"] 
                                   and not m.get("read", False))
                        
                        # Create a row for each mentor
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            if st.button(
                                f"{mentor.get('name', mentor['email'])}",
                                key=f"chat_btn_{mentor['email']}"
                            ):
                                st.session_state['chat_user'] = mentor['email']
                                st.session_state['chat_room'] = None
                                st.session_state['active_tab'] = 3  # Chat tab for intern
                                st.rerun()
                        with col2:
                            if unread > 0:
                                st.markdown(f"<span style='color: #ff4b4b'>({unread})</span>", 
                                          unsafe_allow_html=True)
            else:
                # Show interns list
                interns = db.get_users_by_role("intern")
                if interns:
                    selected_intern = st.selectbox(
                        "Select Intern to Chat",
                        options=[i["email"] for i in interns],
                        format_func=lambda x: db.get_user_name(x)
                    )
                    if selected_intern:
                        if st.button("Chat with Intern"):
                            st.session_state['chat_user'] = selected_intern
                            st.session_state['chat_room'] = None
                            st.session_state['active_tab'] = 4  # Chat tab for mentor
                            st.rerun()
            
            # General chat room option
            if st.button("General Chat Room"):
                st.session_state['chat_user'] = None
                st.session_state['chat_room'] = None
                st.session_state['active_tab'] = 4 if role == "mentor" else 3
                st.rerun()
        
        with rooms_tab:
            # Initialize room categories if they don't exist
            try:
                existing_rooms = db.get_chat_rooms()
                if not existing_rooms:
                    # Create default room categories
                    room_categories = [
                        {"name": "offer-letter", "purpose": "Questions about internship confirmation or delays"},
                        {"name": "task-issues", "purpose": "Clarifications or blockers on assignments"},
                        {"name": "exams", "purpose": "Leave or break requests for exams or events"},
                        {"name": "general", "purpose": "Watercooler chat or casual discussion"},
                        {"name": "bugs-feedback", "purpose": "Report issues or suggest improvements"}
                    ]
                    
                    for room in room_categories:
                        db.add_chat_room(room["name"], room["purpose"])
                    
                    # Fetch rooms again after creating them
                    existing_rooms = db.get_chat_rooms()
            except Exception as e:
                st.error(f"Error initializing chat rooms: {str(e)}")
                existing_rooms = []
            
            # Display room categories
            for room in existing_rooms:
                room_name = room.get("name", "")
                room_purpose = room.get("purpose", "")
                
                # Create a button for each room
                if st.button(
                    f"#{room_name}",
                    key=f"room_btn_{room_name}",
                    help=room_purpose
                ):
                    # Update session state and force rerun
                    st.session_state['chat_user'] = None
                    st.session_state['chat_room'] = room_name
                    # Set active tab to chat tab (3 for intern, 4 for mentor)
                    st.session_state['active_tab'] = 4 if role == "mentor" else 3
                    st.rerun()
                
                # Show room purpose as a tooltip/caption
                if room_purpose:
                    st.caption(f"{room_purpose[:40]}..." if len(room_purpose) > 40 else room_purpose)
        
        with meetings_tab:
            # Get recent meetings
            recent_meetings = db.get_recent_meetings(limit=10)
            
            if recent_meetings:
                st.write("#### Recent Meetings")
                
                for meeting in recent_meetings:
                    meeting_time = meeting.get("created_at", datetime.now()).strftime("%m/%d %I:%M %p")
                    room_name = meeting.get("room_name", "Unknown")
                    meeting_link = meeting.get("meeting_link", "#")
                    creator = db.get_user_name(meeting.get("created_by", "Unknown"))
                    
                    # Create a collapsible section for each meeting
                    with st.expander(f"{room_name} ({meeting_time})"):
                        st.write(f"Created by: {creator}")
                        st.write(f"Room: {room_name}")
                        
                        # Join button
                        if st.button("🎥 Join", key=f"join_meeting_{str(meeting.get('_id', ''))}"):
                            st.markdown(f'<script>window.open("{meeting_link}", "_blank");</script>', unsafe_allow_html=True)
                            st.success(f"Opening meeting...")
            else:
                st.info("No recent meetings found. Create one by clicking 'Join Meeting' in any chat room.")
