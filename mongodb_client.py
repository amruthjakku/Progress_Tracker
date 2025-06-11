from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure
import streamlit as st
import certifi
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Constants for connection retry
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

@st.cache_resource
def get_mongo_client():
    """
    Get a MongoDB client with retry logic and improved error handling.
    Uses Streamlit's cache_resource to maintain a single connection across reruns.
    """
    uri = os.getenv("MONGODB_URI", "mongodb+srv://amruthjakku:jS7fK5f2QwMZANut@cluster0.hc4q6ax.mongodb.net/")
    
    for attempt in range(MAX_RETRIES):
        try:
            # Create MongoDB client with increased timeout
            client = MongoClient(
                uri,
                tlsCAFile=certifi.where(),
                serverSelectionTimeoutMS=10000,  # Increased timeout
                connectTimeoutMS=10000,
                socketTimeoutMS=20000,
                maxIdleTimeMS=45000,
                retryWrites=True,
                w="majority"  # Ensure writes are acknowledged by majority of replicas
            )
            
            # Test connection
            client.admin.command('ping')
            print("MongoDB connection successful")
            return client
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            # Connection-specific errors
            print(f"MongoDB connection attempt {attempt+1} failed: {str(e)}")
            if attempt < MAX_RETRIES - 1:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                # Final attempt failed
                if not isinstance(e, st.runtime.scriptrunner.StopException):
                    st.error(f"Could not connect to MongoDB after {MAX_RETRIES} attempts: {str(e)}")
                raise e
                
        except OperationFailure as e:
            # Authentication or operation errors
            print(f"MongoDB operation failed: {str(e)}")
            if not isinstance(e, st.runtime.scriptrunner.StopException):
                st.error(f"MongoDB authentication or operation error: {str(e)}")
            raise e
            
        except Exception as e:
            # Other unexpected errors
            print(f"Unexpected MongoDB error: {str(e)}")
            if not isinstance(e, st.runtime.scriptrunner.StopException):
                st.error(f"Unexpected error connecting to MongoDB: {str(e)}")
            raise e
