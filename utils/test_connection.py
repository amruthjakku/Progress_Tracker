import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mongodb_client import get_mongo_client

def test_connection():
    try:
        client = get_mongo_client()
        db = client.progress_tracker
        
        # Try to write a test document
        result = db.test.insert_one({"test": True})
        print("Successfully wrote to MongoDB!")
        
        # Clean up
        db.test.delete_one({"_id": result.inserted_id})
        print("Test complete!")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_connection()
