import streamlit as st
import time
from datetime import datetime
from models.database import DatabaseManager
from utils.huggingface_chatbot import get_ai_assistant_response
from utils.gemini_api import get_gemini_response

def render_ai_assistant(user_email, user_id=None):
    """
    Render an AI assistant chat interface that can help interns with their tasks
    and provide guidance based on their progress.
    
    Args:
        user_email (str): The user's email
        user_id (str): Optional user ID
    """
    st.write("### 🤖 AI Assistant")
    st.caption("Ask me anything about your tasks, progress, or for general guidance!")
    
    # Initialize database manager
    db = DatabaseManager()
    
    # Initialize chat history in session state if not exists
    if 'ai_chat_history' not in st.session_state:
        st.session_state.ai_chat_history = []
    
    # Get user context for more personalized responses
    tasks = db.get_user_tasks(user_email)
    metrics = db.get_performance_metrics(user_email)
    
    # Calculate progress stats
    total_tasks = len(tasks)
    completed_tasks = sum(1 for t in tasks if t.get("progress", {}).get("status") == "done")
    completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    
    # Get current tasks (in progress)
    current_tasks = [t["title"] for t in tasks if t.get("progress", {}).get("status") == "in_progress"]
    
    # User context for the AI
    user_context = {
        "tasks_completed": completed_tasks,
        "total_tasks": total_tasks,
        "progress": f"{completion_percentage:.1f}%",
        "current_tasks": current_tasks,
        "streak_days": metrics.get("streak_days", 0)
    }
    
    # Display chat history
    chat_container = st.container()
    with chat_container:
        for i, message in enumerate(st.session_state.ai_chat_history):
            if i % 2 == 0:  # User message
                with st.chat_message("user"):
                    st.write(message)
            else:  # AI response
                with st.chat_message("assistant", avatar="🤖"):
                    st.write(message)
    
    # Chat input
    user_input = st.chat_input("Ask the AI assistant...")
    
    if user_input:
        # Add user message to chat history
        st.session_state.ai_chat_history.append(user_input)
        
        # Display user message
        with st.chat_message("user"):
            st.write(user_input)
        
        # Display AI thinking indicator
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                # Try to get response directly from Gemini API for simplicity
                try:
                    enhanced_prompt = f"""
                    You are an AI assistant for an intern progress tracking system. 
                    
                    Context about the user:
                    - Tasks completed: {user_context['tasks_completed']} out of {user_context['total_tasks']}
                    - Current progress: {user_context['progress']}
                    - Current tasks: {', '.join(user_context['current_tasks']) if user_context['current_tasks'] else 'None'}
                    - Streak days: {user_context['streak_days']}
                    
                    The intern has asked: {user_input}
                    
                    Please provide a helpful, encouraging response that addresses their question and motivates them to make progress on their tasks.
                    """
                    from utils.gemini_api import get_gemini_response
                    ai_response = get_gemini_response(enhanced_prompt)
                except Exception as e:
                    # Fallback to a simple response if API fails
                    ai_response = f"""
                    I'd be happy to help with your question about "{user_input}".
                    
                    Based on your progress ({user_context['progress']}), you're doing well! 
                    Keep focusing on your current tasks and don't hesitate to ask for help if you need it.
                    
                    Is there anything specific about your tasks that you'd like to discuss?
                    """
                
                # Add a small delay for better UX
                time.sleep(0.5)
                
                # Display AI response
                st.write(ai_response)
        
        # Add AI response to chat history
        st.session_state.ai_chat_history.append(ai_response)
        
        # Save the interaction to the database for future reference
        try:
            db.db.ai_interactions.insert_one({
                "user_email": user_email,
                "user_query": user_input,
                "ai_response": ai_response,
                "timestamp": datetime.now(),
                "context": user_context
            })
        except Exception as e:
            print(f"Error saving AI interaction: {str(e)}")

def render_ai_assistant_sidebar(user_email):
    """Render a sidebar widget for quick access to the AI assistant"""
    with st.sidebar:
        st.write("### 🤖 AI Assistant")
        
        # Quick question templates
        st.caption("Quick questions:")
        
        if st.button("📊 How am I doing?"):
            st.session_state['active_tab'] = 5  # AI Assistant tab
            st.session_state.ai_chat_history.append("How am I doing on my tasks?")
            st.rerun()
            
        if st.button("🔍 What should I work on next?"):
            st.session_state['active_tab'] = 5  # AI Assistant tab
            st.session_state.ai_chat_history.append("What should I work on next?")
            st.rerun()
            
        if st.button("💡 I'm stuck on a task"):
            st.session_state['active_tab'] = 5  # AI Assistant tab
            st.session_state.ai_chat_history.append("I'm stuck on my current task. Can you help?")
            st.rerun()