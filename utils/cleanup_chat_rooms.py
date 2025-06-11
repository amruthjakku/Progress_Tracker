"""
Clean up duplicate chat rooms and ensure all rooms have the required fields.
"""
import sys
import os

# Add the parent directory to the path so we can import the models module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager
from mongodb_client import get_mongo_client

def cleanup_chat_rooms():
    """Clean up chat rooms in the database"""
    db = DatabaseManager()
    client = get_mongo_client()
    mongo_db = client.progress_tracker
    
    # Get all rooms
    rooms = list(mongo_db.chat_rooms.find())
    print(f"Found {len(rooms)} chat rooms")
    
    # Define the standard room categories
    standard_rooms = {
        "offer-letter": "Questions about internship confirmation or delays",
        "task-issues": "Clarifications or blockers on assignments",
        "exams": "Leave or break requests for exams or events",
        "general": "Watercooler chat or casual discussion",
        "bugs-feedback": "Report issues or suggest improvements"
    }
    
    # Delete all existing rooms
    result = mongo_db.chat_rooms.delete_many({})
    print(f"Deleted {result.deleted_count} existing rooms")
    
    # Create standard rooms
    for name, purpose in standard_rooms.items():
        room_id = db.add_chat_room(name, purpose)
        print(f"Created room: #{name} (ID: {room_id})")
    
    # Verify rooms were created
    rooms = db.get_chat_rooms()
    print(f"\nTotal rooms created: {len(rooms)}")
    for room in rooms:
        print(f"- #{room.get('name', 'Unknown')}: {room.get('purpose', 'No purpose')}")

if __name__ == "__main__":
    print("Cleaning up chat rooms...")
    cleanup_chat_rooms()
    print("Done!")