"""
Initialize chat rooms in the database.
Run this script once to create the default chat rooms.
"""
import sys
import os

# Add the parent directory to the path so we can import the models module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import DatabaseManager

def init_chat_rooms():
    """Initialize default chat rooms"""
    db = DatabaseManager()
    
    # Default room categories
    room_categories = [
        {"name": "offer-letter", "purpose": "Questions about internship confirmation or delays"},
        {"name": "task-issues", "purpose": "Clarifications or blockers on assignments"},
        {"name": "exams", "purpose": "Leave or break requests for exams or events"},
        {"name": "general", "purpose": "Watercooler chat or casual discussion"},
        {"name": "bugs-feedback", "purpose": "Report issues or suggest improvements"}
    ]
    
    # Create each room
    for room in room_categories:
        room_id = db.add_chat_room(room["name"], room["purpose"])
        print(f"Created room: #{room['name']} (ID: {room_id})")
    
    # Verify rooms were created
    rooms = db.get_chat_rooms()
    print(f"\nTotal rooms created: {len(rooms)}")
    for room in rooms:
        print(f"- #{room.get('name', 'Unknown')}: {room.get('purpose', 'No purpose')}")

if __name__ == "__main__":
    print("Initializing chat rooms...")
    init_chat_rooms()
    print("Done!")