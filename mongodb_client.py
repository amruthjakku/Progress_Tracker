from pymongo import MongoClient
import streamlit as st
import certifi
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@st.cache_resource
def get_mongo_client():
    try:
        uri = os.getenv("MONGODB_URI", "mongodb+srv://amruthjakku:jS7fK5f2QwMZANut@cluster0.hc4q6ax.mongodb.net/")
        client = MongoClient(
            uri,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=5000
        )
        # Test connection
        client.admin.command('ping')
        return client
    except Exception as e:
        print(f"MongoDB connection error: {str(e)}")  # Print for debugging
        if not isinstance(e, st.runtime.scriptrunner.StopException):
            st.error(f"Could not connect to MongoDB: {str(e)}")
        raise e
