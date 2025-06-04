import streamlit as st
from datetime import datetime
from models.database import DatabaseManager

def render_chat(user_email: str, other_user: str = None):
    """
    Render chat component that can be used in both intern and mentor dashboards
    If other_user is None, it shows a general chat room
    """
    db = DatabaseManager()
    
    # Initialize chat state if not exists
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    
    # Chat container with user info
    if other_user:
        st.write(f"### 💬 Chat with {db.get_user_name(other_user)}")
        # Mark messages from other user as read
        db.mark_messages_read(user_email, other_user)
    else:
        st.write("### 💬 General Chat Room")
    
    # Chat messages container with custom styling
    chat_container = st.container()
    with chat_container:
        # Get messages from database
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
            # Save message to database
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
    """Render chat sidebar with user list and unread message indicators"""
    db = DatabaseManager()
    
    with st.sidebar:
        st.write("### 💬 Chat")
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
                            st.session_state.update({'chat_user': mentor['email']})
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
                    st.button("Chat with Intern",
                             on_click=lambda: st.session_state.update(
                                 {'chat_user': selected_intern}
                             ))
        
        # General chat room option
        st.button("General Chat Room",
                 on_click=lambda: st.session_state.update({'chat_user': None}))
