import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mongodb_client import get_mongo_client
from datetime import datetime

def create_test_user():
    client = get_mongo_client()
    db = client.progress_tracker
    
    # Create test user
    user_data = {
        "email": "intern@example.com",
        "role": "intern",
        "name": "Test Intern",
        "created_at": datetime.now()
    }
    
    try:
        result = db.users.update_one(
            {"email": user_data["email"]},
            {"$set": user_data},
            upsert=True
        )
        print(f"User created/updated successfully!")
        
        # Create a test mentor
        mentor_data = {
            "email": "mentor@example.com",
            "role": "mentor",
            "name": "Test Mentor",
            "created_at": datetime.now()
        }
        
        result = db.users.update_one(
            {"email": mentor_data["email"]},
            {"$set": mentor_data},
            upsert=True
        )
        print(f"Mentor created/updated successfully!")
        
    except Exception as e:
        print(f"Error creating users: {str(e)}")

if __name__ == "__main__":
    create_test_user()
