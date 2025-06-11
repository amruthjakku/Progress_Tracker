import os
import requests
import json
import streamlit as st

# Hugging Face API configuration
HF_API_TOKEN = os.environ.get("HF_API_TOKEN", "")  # Set this in your environment or .env file
HF_API_URL = "https://api-inference.huggingface.co/models/"

# Default model to use if not specified
DEFAULT_MODEL = "mistralai/Mistral-7B-Instruct-v0.2"

class HuggingFaceChatbot:
    """
    A class to interact with Hugging Face models for chatbot functionality.
    This can be used with various models from Hugging Face.
    """
    
    def __init__(self, model_id=None, api_token=None):
        """Initialize the chatbot with a specific model"""
        self.model_id = model_id or DEFAULT_MODEL
        self.api_token = api_token or HF_API_TOKEN
    
    def get_response(self, prompt, conversation_history=None):
        """
        Get a response from the model based on the prompt and conversation history.
        
        Args:
            prompt (str): The user's input prompt
            conversation_history (list): Optional list of previous messages
            
        Returns:
            str: The model's response
        """
        try:
            # Format conversation history for the model
            if conversation_history:
                formatted_prompt = self._format_conversation(conversation_history, prompt)
            else:
                formatted_prompt = prompt
            
            # Make API request to Hugging Face
            headers = {
                "Authorization": f"Bearer {self.api_token}" if self.api_token else "",
                "Content-Type": "application/json"
            }
            
            payload = {
                "inputs": formatted_prompt,
                "parameters": {
                    "max_new_tokens": 512,
                    "temperature": 0.7,
                    "repetition_penalty": 1.2
                }
            }
            
            # Make the API request
            response = requests.post(
                f"{HF_API_URL}{self.model_id}",
                headers=headers,
                json=payload
            )
            
            # Check if the request was successful
            if response.status_code == 200:
                try:
                    # Parse the response
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        return result[0].get("generated_text", "No response generated")
                    else:
                        return str(result)
                except:
                    return response.text
            else:
                # If the request failed, try using the Gemini API as a fallback
                from utils.gemini_api import get_gemini_response
                return get_gemini_response(f"You are an AI assistant for interns. Answer this question: {prompt}")
                
        except Exception as e:
            # If there's an error, try using the Gemini API as a fallback
            try:
                from utils.gemini_api import get_gemini_response
                return get_gemini_response(f"You are an AI assistant for interns. Answer this question: {prompt}")
            except:
                return f"Error generating response: {str(e)}"
    
    def _format_conversation(self, history, new_prompt):
        """Format the conversation history for the model"""
        # This formatting might need to be adjusted based on the specific model
        formatted = ""
        for i, message in enumerate(history):
            role = "User: " if i % 2 == 0 else "Assistant: "
            formatted += f"{role}{message}\n"
        
        formatted += f"User: {new_prompt}\nAssistant:"
        return formatted

def get_ai_assistant_response(prompt, context=None):
    """
    Get a response from the AI assistant with optional context about tasks.
    
    Args:
        prompt (str): The user's question or request
        context (dict): Optional context about the user's tasks or progress
        
    Returns:
        str: The AI assistant's response
    """
    # Initialize the chatbot (lazy loading)
    if "hf_chatbot" not in st.session_state:
        st.session_state.hf_chatbot = HuggingFaceChatbot()
    
    # Add context to the prompt if available
    if context:
        enhanced_prompt = f"""
        Context about the user:
        - Tasks completed: {context.get('tasks_completed', 0)}
        - Current tasks: {context.get('current_tasks', [])}
        - Progress: {context.get('progress', '0%')}
        
        User question: {prompt}
        
        Please provide a helpful response based on the context above.
        """
    else:
        enhanced_prompt = f"""
        You are an AI assistant for interns working on various tasks. 
        The intern has asked: {prompt}
        
        Please provide a helpful, encouraging response.
        """
    
    # Get response from the chatbot
    try:
        response = st.session_state.hf_chatbot.get_response(enhanced_prompt)
        return response
    except Exception as e:
        # Fallback to Gemini API
        try:
            from utils.gemini_api import get_gemini_response
            return get_gemini_response(enhanced_prompt)
        except:
            return f"I'm having trouble connecting to my knowledge base. Please try again later."

# Example usage
if __name__ == "__main__":
    # Test the chatbot
    chatbot = HuggingFaceChatbot()
    response = chatbot.get_response("What are some tips for completing programming tasks efficiently?")
    print(response)