from typing import List, Optional, Dict
from datetime import datetime, timedelta
import pandas as pd
from .schemas import Task, Progress, UserProfile, PerformanceMetrics
from mongodb_client import get_mongo_client

class DatabaseManager:
    def __init__(self):
        self.client = get_mongo_client()
        self.db = self.client.progress_tracker

    def get_user_tasks(self, user_email: str) -> List[dict]:
        """Get all tasks assigned to a user with their progress"""
        tasks = list(self.db.tasks.find({"assigned_to": user_email}))
        progress_records = list(self.db.progress.find({"user_email": user_email}))
        progress_lookup = {p["task_id"]: p for p in progress_records}
        
        for task in tasks:
            task_id = str(task["_id"])
            task["progress"] = progress_lookup.get(task_id, {})
        
        return tasks

    def update_task_progress(self, user_email: str, task_id: str, 
                           status: str, submission_link: Optional[str] = None) -> None:
        """Update task progress and trigger metrics calculation"""
        now = datetime.now()
        update_data = {
            "status": status,
            "updated_at": now
        }
        
        # Get existing progress
        progress = self.db.progress.find_one({"user_email": user_email, "task_id": task_id})
        
        if status == "in_progress":
            if not progress:
                # New task being started
                update_data["started_at"] = now
            elif progress.get("status") == "done":
                # Task being unmarked as done, keep existing started_at
                if "completed_at" in update_data:
                    update_data.pop("completed_at")
                if "time_spent" in update_data:
                    update_data.pop("time_spent")
        
        if status == "done":
            update_data["completed_at"] = now
            # Calculate time spent
            if progress and progress.get("started_at"):
                time_spent = (now - progress["started_at"]).total_seconds() / 3600  # hours
                update_data["time_spent"] = time_spent
        
        if status == "not_started":
            # Reset progress tracking fields
            update_data["started_at"] = None
            update_data["completed_at"] = None
            update_data["time_spent"] = None
        
        if submission_link:
            update_data["submission_link"] = submission_link
        
        self.db.progress.update_one(
            {"user_email": user_email, "task_id": task_id},
            {"$set": update_data},
            upsert=True
        )
        
        # Update performance metrics
        self._update_performance_metrics(user_email)

    def get_performance_metrics(self, user_email: str, period: str = "weekly") -> dict:
        """Get user's performance metrics"""
        now = datetime.now()
        if period == "daily":
            start_date = now - timedelta(days=1)
        elif period == "weekly":
            start_date = now - timedelta(days=7)
        elif period == "monthly":
            start_date = now - timedelta(days=30)
        
        metrics = self.db.performance_metrics.find_one({
            "user_email": user_email,
            "period": period,
            "date": {"$gte": start_date}
        })
        
        return metrics or {}

    def _update_performance_metrics(self, user_email: str) -> None:
        """Calculate and update user's performance metrics"""
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        
        # Get completed tasks in the last week
        completed_tasks = list(self.db.progress.find({
            "user_email": user_email,
            "status": "done",
            "completed_at": {"$gte": week_ago}
        }))
        
        # Calculate metrics
        tasks_completed = len(completed_tasks)
        total_time = sum(task.get("time_spent", 0) for task in completed_tasks)
        avg_time = total_time / tasks_completed if tasks_completed > 0 else 0
        
        # Calculate streak
        streak = self._calculate_streak(user_email)
        
        # Update metrics
        metrics = {
            "user_email": user_email,
            "period": "weekly",
            "date": now,
            "tasks_completed": tasks_completed,
            "average_task_time": avg_time,
            "streak_days": streak
        }
        
        self.db.performance_metrics.update_one(
            {"user_email": user_email, "period": "weekly"},
            {"$set": metrics},
            upsert=True
        )

    def _calculate_streak(self, user_email: str) -> int:
        """Calculate user's current streak of daily task completion"""
        now = datetime.now()
        streak = 0
        current_date = now.date()
        
        while True:
            # Check if any task was completed on this date
            completed_task = self.db.progress.find_one({
                "user_email": user_email,
                "status": "done",
                "completed_at": {
                    "$gte": datetime.combine(current_date, datetime.min.time()),
                    "$lt": datetime.combine(current_date + timedelta(days=1), datetime.min.time())
                }
            })
            
            if not completed_task:
                break
                
            streak += 1
            current_date -= timedelta(days=1)
        
        return streak

    def get_task_dependencies(self, task_id: str) -> dict:
        """Get task dependencies and their status"""
        task = self.db.tasks.find_one({"_id": task_id})
        if not task or not task.get("prerequisites"):
            return {}
            
        dependencies = {}
        for prereq_id in task["prerequisites"]:
            prereq_task = self.db.tasks.find_one({"_id": prereq_id})
            if prereq_task:
                progress = self.db.progress.find_one({
                    "task_id": str(prereq_id),
                    "user_email": task["assigned_to"]
                })
                dependencies[prereq_task["title"]] = progress.get("status", "not_started") if progress else "not_started"
        
        return dependencies

    def save_chat_message(self, sender_email: str, message: str, recipient_email: Optional[str] = None) -> None:
        """Save a chat message to the database"""
        message_data = {
            "sender_email": sender_email,
            "sender_name": self.get_user_name(sender_email),
            "message": message,
            "timestamp": datetime.now(),
            "recipient_email": recipient_email,
            "read": False
        }
        self.db.chat_messages.insert_one(message_data)

    def get_chat_messages(self, user_email: str, other_user: Optional[str] = None) -> List[dict]:
        """Get chat messages for a user"""
        if other_user:
            # Get direct messages between two users
            query = {
                "$or": [
                    {"sender_email": user_email, "recipient_email": other_user},
                    {"sender_email": other_user, "recipient_email": user_email}
                ]
            }
        else:
            # Get general chat room messages
            query = {"recipient_email": None}
        
        messages = list(self.db.chat_messages.find(query).sort("timestamp", 1))
        return messages

    def mark_messages_read(self, recipient_email: str, sender_email: str) -> None:
        """Mark all messages from sender to recipient as read"""
        self.db.chat_messages.update_many(
            {
                "sender_email": sender_email,
                "recipient_email": recipient_email,
                "read": False
            },
            {"$set": {"read": True}}
        )

    def get_users_by_role(self, role: str) -> List[dict]:
        """Get all users with a specific role"""
        return list(self.db.users.find({"role": role}))

    def get_user_name(self, email: str) -> str:
        """Get user's name from email"""
        user = self.db.users.find_one({"email": email})
        return user.get("name", email) if user else email

    def add_task_category(self, name: str, description: str, color: str) -> str:
        """Add a new task category"""
        category = {
            "name": name,
            "description": description,
            "color": color,
            "created_at": datetime.now()
        }
        result = self.db.task_categories.insert_one(category)
        return str(result.inserted_id)

    def get_task_categories(self) -> List[dict]:
        """Get all task categories"""
        return list(self.db.task_categories.find())
        
    def add_chat_room(self, name: str, purpose: str) -> str:
        """Add a new chat room category"""
        try:
            # Check if room already exists
            existing_room = self.db.chat_rooms.find_one({"name": name})
            if existing_room:
                return str(existing_room["_id"])
                
            room = {
                "name": name,
                "purpose": purpose,
                "created_at": datetime.now()
            }
            result = self.db.chat_rooms.insert_one(room)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error adding chat room: {str(e)}")
            return None
        
    def get_chat_rooms(self) -> List[dict]:
        """Get all chat room categories"""
        try:
            return list(self.db.chat_rooms.find())
        except Exception as e:
            print(f"Error getting chat rooms: {str(e)}")
            return []
        
    def save_room_chat_message(self, sender_email: str, message: str, room_name: str) -> None:
        """Save a chat message to a specific room"""
        try:
            print(f"Saving message to room: {room_name} from {sender_email}")
            message_data = {
                "sender_email": sender_email,
                "sender_name": self.get_user_name(sender_email),
                "message": message,
                "timestamp": datetime.now(),
                "room": room_name,
                "read": False
            }
            result = self.db.chat_messages.insert_one(message_data)
            print(f"Message saved with ID: {result.inserted_id}")
        except Exception as e:
            print(f"Error saving room chat message: {str(e)}")
        
    def get_room_chat_messages(self, room_name: str) -> List[dict]:
        """Get chat messages for a specific room"""
        try:
            print(f"Getting messages for room: {room_name}")
            query = {"room": room_name}
            messages = list(self.db.chat_messages.find(query).sort("timestamp", 1))
            print(f"Found {len(messages)} messages for room {room_name}")
            return messages
        except Exception as e:
            print(f"Error getting room chat messages: {str(e)}")
            return []
