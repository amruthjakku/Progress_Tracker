from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import pymongo
from pymongo.errors import ConnectionFailure, OperationFailure, NetworkTimeout
import time
import random
import string
import json
import os
import re
from bson import ObjectId

class DatabaseManager:
    """Database manager for the Progress Tracker application"""
    
    def __init__(self):
        """Initialize the database manager"""
        from mongodb_client import get_mongo_client
        
        # Get MongoDB client
        self.client = get_mongo_client()
        self.db = self.client["progress_tracker"]
        
        # Initialize collections if they don't exist
        self._initialize_collections()
        
    def _initialize_collections(self):
        """Initialize collections if they don't exist"""
        # List of collections to initialize
        collections = [
            "users", "tasks", "progress", "chat_rooms", "chat_messages", 
            "attendance", "allowed_networks", "notifications"
        ]
        
        # Create collections if they don't exist
        existing_collections = self.db.list_collection_names()
        for collection in collections:
            if collection not in existing_collections:
                self.db.create_collection(collection)
                
        # Create indexes for better performance
        self.db.users.create_index("email", unique=True)
        self.db.tasks.create_index("task_id")
        self.db.progress.create_index([("user_email", 1), ("task_id", 1)])
        self.db.chat_messages.create_index("timestamp")
        self.db.attendance.create_index("timestamp")
        
    def _execute_db_operation(self, operation_func, max_retries=3, retry_delay=1):
        """
        Execute a database operation with retry logic
        
        Args:
            operation_func: Function to execute
            max_retries: Maximum number of retries
            retry_delay: Delay between retries in seconds
            
        Returns:
            Result of the operation
        """
        for attempt in range(max_retries):
            try:
                return operation_func()
            except (ConnectionFailure, NetworkTimeout) as e:
                if attempt < max_retries - 1:
                    print(f"Database connection issue. Retrying... ({attempt+1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    raise e
        
        # If we get here, all retries failed
        raise Exception(f"Failed to execute database operation after {max_retries} attempts")
        
    def get_user_tasks(self, user_email: str) -> List[dict]:
        """
        Get all tasks for a user
        
        Args:
            user_email: Email of the user
            
        Returns:
            List of tasks with progress information
        """
        def operation():
            # Get all tasks
            tasks = list(self.db.tasks.find())
            
            # Get progress for each task
            for task in tasks:
                progress = self.db.progress.find_one({
                    "task_id": str(task["_id"]),
                    "user_email": user_email
                })
                
                # Add progress information to the task
                task["progress"] = progress if progress else {
                    "status": "not_started",
                    "last_updated": None,
                    "completion_date": None,
                    "notes": "",
                    "links": []
                }
                
                # Convert ObjectId to string for JSON serialization
                task["_id"] = str(task["_id"])
                
                # Check if task can be started (all prerequisites are completed)
                task["can_start"] = self.can_start_task(str(task["_id"]), user_email)
                
            return tasks
        
        try:
            # Execute with retry logic
            return self._execute_db_operation(operation)
        except Exception as e:
            print(f"Error getting user tasks: {str(e)}")
            return []
            
    def update_task_progress(self, task_id: str, user_email: str, status: str, 
                           notes: str = None, links: List[str] = None) -> bool:
        """
        Update progress for a task
        
        Args:
            task_id: ID of the task
            user_email: Email of the user
            status: Status of the task (not_started, in_progress, done)
            notes: Notes for the task
            links: List of links for the task
            
        Returns:
            True if successful, False otherwise
        """
        def operation():
            # Get existing progress
            existing_progress = self.db.progress.find_one({
                "task_id": task_id,
                "user_email": user_email
            })
            
            # Create or update progress
            if existing_progress:
                # Update existing progress
                update_data = {
                    "status": status,
                    "last_updated": datetime.now()
                }
                
                # Add completion date if task is done
                if status == "done" and existing_progress.get("status") != "done":
                    update_data["completion_date"] = datetime.now()
                
                # Add notes and links if provided
                if notes is not None:
                    update_data["notes"] = notes
                if links is not None:
                    update_data["links"] = links
                
                result = self.db.progress.update_one(
                    {"_id": existing_progress["_id"]},
                    {"$set": update_data}
                )
                
                return result.modified_count > 0
            else:
                # Create new progress
                progress_data = {
                    "task_id": task_id,
                    "user_email": user_email,
                    "status": status,
                    "last_updated": datetime.now(),
                    "notes": notes if notes is not None else "",
                    "links": links if links is not None else []
                }
                
                # Add completion date if task is done
                if status == "done":
                    progress_data["completion_date"] = datetime.now()
                
                result = self.db.progress.insert_one(progress_data)
                return result.inserted_id is not None
        
        try:
            # Execute with retry logic
            return self._execute_db_operation(operation)
        except Exception as e:
            print(f"Error updating task progress: {str(e)}")
            return False
            
    def get_task_dependencies(self, task_id: str) -> dict:
        """
        Get dependencies for a task
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dictionary with prerequisites and dependents
        """
        def operation():
            # Get the task
            task = self.db.tasks.find_one({"_id": ObjectId(task_id)})
            if not task:
                return {"prerequisites": [], "dependents": []}
                
            # Get prerequisites
            prerequisites = []
            if "prerequisites" in task:
                for prereq_id in task["prerequisites"]:
                    prereq = self.db.tasks.find_one({"_id": ObjectId(prereq_id)})
                    if prereq:
                        prerequisites.append({
                            "_id": str(prereq["_id"]),
                            "title": prereq["title"],
                            "category": prereq.get("category", "Uncategorized")
                        })
            
            # Get dependents (tasks that have this task as a prerequisite)
            dependents = []
            dependent_tasks = self.db.tasks.find({"prerequisites": str(task["_id"])})
            for dep in dependent_tasks:
                dependents.append({
                    "_id": str(dep["_id"]),
                    "title": dep["title"],
                    "category": dep.get("category", "Uncategorized")
                })
                
            return {
                "prerequisites": prerequisites,
                "dependents": dependents
            }
        
        try:
            # Execute with retry logic
            return self._execute_db_operation(operation)
        except Exception as e:
            print(f"Error getting task dependencies: {str(e)}")
            return {"prerequisites": [], "dependents": []}
            
    def can_start_task(self, task_id: str, user_email: str) -> bool:
        """
        Check if a task can be started (all prerequisites are completed)
        
        Args:
            task_id: ID of the task
            user_email: Email of the user
            
        Returns:
            True if the task can be started, False otherwise
        """
        try:
            # Get the task
            task = self.db.tasks.find_one({"_id": ObjectId(task_id)})
            if not task:
                return False
                
            # If no prerequisites, task can be started
            if "prerequisites" not in task or not task["prerequisites"]:
                return True
                
            # Check if all prerequisites are completed
            for prereq_id in task["prerequisites"]:
                prereq_id = str(prereq_id)
                progress = self.db.progress.find_one({
                    "task_id": prereq_id,
                    "user_email": user_email
                })
                
                # If any prerequisite is not completed, return False
                if not progress or progress.get("status") != "done":
                    return False
            
            # All prerequisites are completed
            return True
        except Exception as e:
            print(f"Error checking if task can be started: {str(e)}")
            return False
            
    def log_attendance(self, intern_email: str, status: str, network_info: dict) -> str:
        """
        Log attendance for an intern
        
        Args:
            intern_email: Email of the intern
            status: Status of the attendance (check-in or check-out)
            network_info: Network information (SSID, IP, etc.)
            
        Returns:
            ID of the created attendance record
        """
        def operation():
            try:
                # Validate inputs
                if not intern_email or not status or not network_info:
                    print("Invalid attendance inputs")
                    return None
                    
                # Ensure status is valid
                if status not in ["check-in", "check-out"]:
                    print(f"Invalid attendance status: {status}")
                    return None
                
                # Create attendance record with enhanced network info
                attendance = {
                    "intern_email": intern_email,
                    "timestamp": datetime.now(),
                    "status": status,
                    "network_info": network_info,
                    "ip_address": network_info.get("ip", "Unknown"),
                    "device_info": {
                        "hostname": network_info.get("hostname", "Unknown"),
                        "platform": network_info.get("platform", "Unknown"),
                        "user_agent": network_info.get("user_agent", "Unknown")
                    },
                    "verification_method": "ip_based"
                }
                
                result = self.db.attendance.insert_one(attendance)
                return str(result.inserted_id)
            except Exception as e:
                print(f"Error in log_attendance operation: {str(e)}")
                return None
        
        try:
            # Execute with retry logic
            return self._execute_db_operation(operation)
        except Exception as e:
            print(f"Error logging attendance: {str(e)}")
            return None
            
    def get_allowed_networks(self) -> dict:
        """
        Get allowed networks configuration from database
        
        Returns:
            Dictionary with allowed networks configuration
        """
        def operation():
            # Get configuration from database
            config = self.db.allowed_networks.find_one({"type": "network_config"})
            
            # If no configuration exists, create a default one
            if not config:
                default_config = {
                    "type": "network_config",
                    "ip_ranges": ["127.0.0.1", "192.168.1.0/24"],
                    "ssids": ["Office WiFi", "Company Network"],
                    "domains": ["company.com", "office.local"],
                    "last_updated": datetime.now(),
                    "updated_by": "system"
                }
                
                self.db.allowed_networks.insert_one(default_config)
                return default_config
                
            return config
        
        try:
            # Execute with retry logic
            return self._execute_db_operation(operation)
        except Exception as e:
            print(f"Error getting allowed networks: {str(e)}")
            return {
                "ip_ranges": ["127.0.0.1"],
                "ssids": [],
                "domains": []
            }
            
    def update_allowed_networks(self, networks: dict, updated_by: str) -> bool:
        """
        Update allowed networks configuration
        
        Args:
            networks: Dictionary with allowed networks configuration
            updated_by: Email of the user who updated the configuration
            
        Returns:
            True if successful, False otherwise
        """
        def operation():
            # Update configuration in database
            result = self.db.allowed_networks.update_one(
                {"type": "network_config"},
                {"$set": {
                    **networks,
                    "last_updated": datetime.now(),
                    "updated_by": updated_by
                }},
                upsert=True
            )
            
            return result.modified_count > 0 or result.upserted_id is not None
        
        try:
            # Execute with retry logic
            return self._execute_db_operation(operation)
        except Exception as e:
            print(f"Error updating allowed networks: {str(e)}")
            return False
            
    def add_allowed_network(self, network_type: str, value: str, updated_by: str) -> bool:
        """
        Add a new allowed network
        
        Args:
            network_type: Type of network (ip_ranges, ssids, domains)
            value: Value to add
            updated_by: Email of the user who updated the configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current configuration
            networks = self.get_allowed_networks()
            
            # Add value if it doesn't exist
            if network_type in networks and value not in networks[network_type]:
                networks[network_type].append(value)
                
            # Update configuration
            return self.update_allowed_networks(networks, updated_by)
        except Exception as e:
            print(f"Error adding allowed network: {str(e)}")
            return False
            
    def remove_allowed_network(self, network_type: str, value: str, updated_by: str) -> bool:
        """
        Remove an allowed network
        
        Args:
            network_type: Type of network (ip_ranges, ssids, domains)
            value: Value to remove
            updated_by: Email of the user who updated the configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current configuration
            networks = self.get_allowed_networks()
            
            # Remove value if it exists
            if network_type in networks and value in networks[network_type]:
                networks[network_type].remove(value)
                
            # Update configuration
            return self.update_allowed_networks(networks, updated_by)
        except Exception as e:
            print(f"Error removing allowed network: {str(e)}")
            return False
            
    def get_today_attendance(self, intern_email: str) -> dict:
        """
        Get today's attendance for an intern
        
        Args:
            intern_email: Email of the intern
            
        Returns:
            Dictionary with check-in and check-out information
        """
        def operation():
            try:
                # Get today's date range
                today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                tomorrow = today + timedelta(days=1)
                
                # Get attendance records for today
                records = list(self.db.attendance.find({
                    "intern_email": intern_email,
                    "timestamp": {
                        "$gte": today,
                        "$lt": tomorrow
                    }
                }).sort("timestamp", 1))
                
                # Process records to get check-in and check-out times
                check_in = None
                check_out = None
                
                for record in records:
                    if record.get("status") == "check-in" and (check_in is None or record["timestamp"] < check_in["timestamp"]):
                        check_in = record
                    elif record.get("status") == "check-out" and (check_out is None or record["timestamp"] > check_out["timestamp"]):
                        check_out = record
                
                # Calculate duration if both check-in and check-out exist
                duration = None
                if check_in and check_out and "timestamp" in check_in and "timestamp" in check_out:
                    try:
                        duration = (check_out["timestamp"] - check_in["timestamp"]).total_seconds() / 3600  # hours
                    except Exception as e:
                        print(f"Error calculating duration: {str(e)}")
                        duration = None
                
                return {
                    "check_in": check_in["timestamp"] if check_in and "timestamp" in check_in else None,
                    "check_out": check_out["timestamp"] if check_out and "timestamp" in check_out else None,
                    "duration": duration,
                    "status": "Present" if check_in else "Absent"
                }
            except Exception as e:
                print(f"Error in get_today_attendance operation: {str(e)}")
                return {
                    "check_in": None,
                    "check_out": None,
                    "duration": None,
                    "status": "Error"
                }
        
        try:
            # Execute with retry logic
            result = self._execute_db_operation(operation)
            
            # Validate the result
            if not isinstance(result, dict):
                print(f"Invalid result type from get_today_attendance: {type(result)}")
                return {
                    "check_in": None,
                    "check_out": None,
                    "duration": None,
                    "status": "Error"
                }
                
            return result
        except Exception as e:
            print(f"Error getting today's attendance: {str(e)}")
            return {
                "check_in": None,
                "check_out": None,
                "duration": None,
                "status": "Unknown"
            }
            
    def get_attendance_stats(self, days: int = 30) -> List[dict]:
        """
        Get attendance statistics for all interns
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of attendance statistics for each intern
        """
        def operation():
            try:
                # Get date range
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                # Get all interns
                interns = list(self.db.users.find({"role": "intern"}))
                
                # Get attendance records for all interns
                attendance_records = list(self.db.attendance.find({
                    "timestamp": {
                        "$gte": start_date,
                        "$lte": end_date
                    }
                }))
                
                # Group attendance records by day and intern
                attendance_by_day = {}
                for record in attendance_records:
                    day = record["timestamp"].strftime("%Y-%m-%d")
                    email = record["intern_email"]
                    
                    if day not in attendance_by_day:
                        attendance_by_day[day] = {}
                        
                    if email not in attendance_by_day[day]:
                        attendance_by_day[day][email] = {
                            "check_in": None,
                            "check_out": None,
                            "status": "Absent"
                        }
                        
                    if record["status"] == "check-in" and (attendance_by_day[day][email]["check_in"] is None or 
                                                         record["timestamp"] < attendance_by_day[day][email]["check_in"]):
                        attendance_by_day[day][email]["check_in"] = record["timestamp"]
                        attendance_by_day[day][email]["status"] = "Present"
                        
                    if record["status"] == "check-out" and (attendance_by_day[day][email]["check_out"] is None or 
                                                          record["timestamp"] > attendance_by_day[day][email]["check_out"]):
                        attendance_by_day[day][email]["check_out"] = record["timestamp"]
                
                # Calculate statistics for each intern
                stats_by_intern = {}
                for intern in interns:
                    email = intern["email"]
                    stats_by_intern[email] = {
                        "intern_email": email,
                        "intern_name": intern.get("name", email),
                        "days_present": 0,
                        "days_absent": 0,
                        "on_time_days": 0,
                        "late_days": 0,
                        "total_hours": 0,
                        "avg_hours": 0,
                        "attendance_rate": 0,
                        "punctuality_rate": 0
                    }
                
                # Calculate working days (excluding weekends)
                working_days = sum(1 for day in (start_date + timedelta(days=i) for i in range(days))
                                  if day.weekday() < 5)  # Monday to Friday
                
                # Process attendance records
                for day, interns_attendance in attendance_by_day.items():
                    for email, attendance in interns_attendance.items():
                        if email in stats_by_intern:
                            if attendance["status"] == "Present":
                                stats_by_intern[email]["days_present"] += 1
                                
                                # Calculate duration
                                if attendance["check_in"] and attendance["check_out"]:
                                    duration = (attendance["check_out"] - attendance["check_in"]).total_seconds() / 3600  # hours
                                    stats_by_intern[email]["total_hours"] += duration
                                
                                # Check if on time (before 9:30 AM)
                                if attendance["check_in"] and (attendance["check_in"].hour < 9 or 
                                                             (attendance["check_in"].hour == 9 and attendance["check_in"].minute <= 30)):
                                    stats_by_intern[email]["on_time_days"] += 1
                                else:
                                    stats_by_intern[email]["late_days"] += 1
                
                # Calculate statistics
                for email, stats in stats_by_intern.items():
                    stats["days_absent"] = working_days - stats["days_present"]
                    stats["attendance_rate"] = (stats["days_present"] / working_days * 100) if working_days > 0 else 0
                    stats["avg_hours"] = (stats["total_hours"] / stats["days_present"]) if stats["days_present"] > 0 else 0
                    stats["punctuality_rate"] = (stats["on_time_days"] / stats["days_present"] * 100) if stats["days_present"] > 0 else 0
                
                return list(stats_by_intern.values())
            except Exception as e:
                print(f"Error in get_attendance_stats operation: {str(e)}")
                return []
        
        try:
            # Execute with retry logic
            return self._execute_db_operation(operation)
        except Exception as e:
            print(f"Error getting attendance statistics: {str(e)}")
            return []
    
    def get_attendance_history(self, intern_email: str = None, days: int = 30) -> List[dict]:
        """
        Get attendance history for an intern or all interns
        
        Args:
            intern_email: Email of the intern (None for all interns)
            days: Number of days to look back
            
        Returns:
            List of attendance records
        """
        def operation():
            try:
                # Ensure days is a valid integer
                try:
                    days_int = int(days)
                    if days_int <= 0:
                        days_int = 30  # Default to 30 days if invalid
                except (TypeError, ValueError):
                    days_int = 30  # Default to 30 days if conversion fails
                
                # Get date range
                try:
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=days_int)
                except Exception:
                    # Fallback to hardcoded dates if datetime operations fail
                    from datetime import date
                    end_date = datetime.now()
                    start_date = datetime(end_date.year, end_date.month, 1)  # First day of current month
                
                # Get attendance records
                query = {
                    "timestamp": {
                        "$gte": start_date,
                        "$lte": end_date
                    }
                }
                
                # Add intern_email filter if provided
                if intern_email:
                    query["intern_email"] = intern_email
                    
                records = list(self.db.attendance.find(query).sort("timestamp", -1))
                
                # Group records by intern and day
                attendance_by_key = {}
                for record in records:
                    try:
                        if "intern_email" not in record or "timestamp" not in record:
                            continue  # Skip invalid records
                            
                        email = record["intern_email"]
                        day = record["timestamp"].strftime("%Y-%m-%d")
                        key = f"{email}_{day}" if intern_email is None else day
                        
                        if key not in attendance_by_key:
                            attendance_by_key[key] = {
                                "intern_email": email,
                                "date": record["timestamp"].date(),
                                "check_in": None,
                                "check_out": None,
                                "status": "Absent"
                            }
                        
                        if record.get("status") == "check-in" and (attendance_by_key[key]["check_in"] is None or 
                                                                record["timestamp"] < attendance_by_key[key]["check_in"]):
                            attendance_by_key[key]["check_in"] = record["timestamp"]
                            attendance_by_key[key]["status"] = "Present"
                        
                        if record.get("status") == "check-out" and (attendance_by_key[key]["check_out"] is None or 
                                                                record["timestamp"] > attendance_by_key[key]["check_out"]):
                            attendance_by_key[key]["check_out"] = record["timestamp"]
                    except Exception as e:
                        print(f"Error processing attendance record: {str(e)}")
                        continue  # Skip this record and continue with others
                
                # Calculate duration for each record
                for key, data in attendance_by_key.items():
                    try:
                        if data["check_in"] and data["check_out"]:
                            data["duration"] = (data["check_out"] - data["check_in"]).total_seconds() / 3600  # hours
                        else:
                            data["duration"] = None
                            
                        # Add intern name if available
                        if intern_email is None:
                            try:
                                user = self.db.users.find_one({"email": data["intern_email"]})
                                data["intern_name"] = user.get("name", data["intern_email"]) if user else data["intern_email"]
                            except Exception:
                                data["intern_name"] = data["intern_email"]
                        
                        # Add IP verification information
                        # Find the check-in record to get IP address and verification method
                        try:
                            check_in_record = next((r for r in records if r.get("intern_email") == data["intern_email"] and 
                                                "timestamp" in r and r["timestamp"].strftime("%Y-%m-%d") == data["date"].strftime("%Y-%m-%d") and
                                                r.get("status") == "check-in"), None)
                            
                            if check_in_record:
                                data["ip_address"] = check_in_record.get("ip_address", "Unknown")
                                data["verification_method"] = check_in_record.get("verification_method", "Unknown")
                                data["device_info"] = check_in_record.get("device_info", {})
                            else:
                                data["ip_address"] = "Unknown"
                                data["verification_method"] = "Unknown"
                                data["device_info"] = {}
                        except Exception:
                            data["ip_address"] = "Unknown"
                            data["verification_method"] = "Unknown"
                            data["device_info"] = {}
                    except Exception as e:
                        print(f"Error processing attendance data for {key}: {str(e)}")
                        # Ensure this record has valid data even if processing fails
                        attendance_by_key[key] = {
                            "intern_email": data.get("intern_email", "Unknown"),
                            "date": data.get("date", datetime.now().date()),
                            "check_in": None,
                            "check_out": None,
                            "duration": None,
                            "status": "Error",
                            "ip_address": "Unknown",
                            "verification_method": "Unknown",
                            "device_info": {}
                        }
                
                return list(attendance_by_key.values())
            except Exception as e:
                print(f"Error in get_attendance_history operation: {str(e)}")
                return []  # Return empty list on error
        
        try:
            # Execute with retry logic
            result = self._execute_db_operation(operation)
            
            # Validate the result
            if not isinstance(result, list):
                print(f"Invalid result type from get_attendance_history: {type(result)}")
                return []
                
            return result
        except Exception as e:
            print(f"Error getting attendance history: {str(e)}")
            return []
        
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
            rooms = list(self.db.chat_rooms.find().sort("name", 1))
            for room in rooms:
                room["_id"] = str(room["_id"])
            return rooms
        except Exception as e:
            print(f"Error getting chat rooms: {str(e)}")
            return []
        
    def add_chat_message(self, room_id: str, user_email: str, message: str) -> str:
        """Add a new chat message"""
        try:
            # Get user name
            user = self.db.users.find_one({"email": user_email})
            user_name = user.get("name", user_email) if user else user_email
            
            msg = {
                "room_id": room_id,
                "user_email": user_email,
                "user_name": user_name,
                "message": message,
                "timestamp": datetime.now()
            }
            result = self.db.chat_messages.insert_one(msg)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error adding chat message: {str(e)}")
            return None
        
    def get_chat_messages(self, room_id: str, limit: int = 50) -> List[dict]:
        """Get chat messages for a room"""
        try:
            messages = list(self.db.chat_messages.find(
                {"room_id": room_id}
            ).sort("timestamp", -1).limit(limit))
            
            for msg in messages:
                msg["_id"] = str(msg["_id"])
                
            return list(reversed(messages))  # Return in chronological order
        except Exception as e:
            print(f"Error getting chat messages: {str(e)}")
            return []
        
    def get_direct_chat_messages(self, user1: str, user2: str, limit: int = 50) -> List[dict]:
        """Get direct chat messages between two users"""
        try:
            # Get messages where either user is sender and the other is recipient
            messages = list(self.db.chat_messages.find({
                "$or": [
                    {"user_email": user1, "recipient": user2},
                    {"user_email": user2, "recipient": user1}
                ]
            }).sort("timestamp", -1).limit(limit))
            
            for msg in messages:
                msg["_id"] = str(msg["_id"])
                
            return list(reversed(messages))  # Return in chronological order
        except Exception as e:
            print(f"Error getting direct chat messages: {str(e)}")
            return []
        
    def add_direct_message(self, sender: str, recipient: str, message: str) -> str:
        """Add a new direct message"""
        try:
            # Get user names
            sender_user = self.db.users.find_one({"email": sender})
            sender_name = sender_user.get("name", sender) if sender_user else sender
            
            recipient_user = self.db.users.find_one({"email": recipient})
            recipient_name = recipient_user.get("name", recipient) if recipient_user else recipient
            
            msg = {
                "user_email": sender,
                "user_name": sender_name,
                "recipient": recipient,
                "recipient_name": recipient_name,
                "message": message,
                "timestamp": datetime.now(),
                "is_direct": True
            }
            result = self.db.chat_messages.insert_one(msg)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error adding direct message: {str(e)}")
            return None
        
    def get_users(self, role: str = None) -> List[dict]:
        """Get all users, optionally filtered by role"""
        try:
            query = {}
            if role:
                query["role"] = role
                
            users = list(self.db.users.find(query).sort("name", 1))
            for user in users:
                user["_id"] = str(user["_id"])
                
            return users
        except Exception as e:
            print(f"Error getting users: {str(e)}")
            return []
        
    def get_user_name(self, email: str) -> str:
        """Get user's name from email"""
        user = self.db.users.find_one({"email": email})
        return user.get("name", email) if user else email
        
    def create_user(self, email: str, name: str, role: str, skills: List[str] = None, college: str = None) -> str:
        """Create a new user in the database"""
        def operation():
            # Check if user already exists
            existing_user = self.db.users.find_one({"email": email})
            if existing_user:
                # If user exists but we couldn't find it earlier, return the existing ID
                if "_id" in existing_user:
                    return str(existing_user["_id"])
                return None
                
            # Create user data with error handling for datetime
            try:
                joined_date = datetime.now()
            except Exception:
                # Fallback if datetime.now() fails
                joined_date = None
                
            user_data = {
                "email": email,
                "name": name,
                "role": role,
                "skills": skills or [],
                "college": college,
                "joined_date": joined_date
            }
            
            result = self.db.users.insert_one(user_data)
            if result and result.inserted_id:
                return str(result.inserted_id)
            return None
            
        try:
            # Execute with retry logic
            return self._execute_db_operation(operation)
        except Exception as e:
            print(f"Error creating user: {str(e)}")
            return None
            
    def import_interns_from_csv(self, csv_data) -> dict:
        """
        Import multiple interns from CSV data
        
        Expected CSV format:
        email,name,college,skills
        
        Returns:
            Dictionary with success and error counts
        """
        try:
            import csv
            from io import StringIO
            
            result = {
                "success": 0,
                "errors": 0,
                "error_details": []
            }
            
            # Parse CSV data
            csv_file = StringIO(csv_data)
            reader = csv.DictReader(csv_file)
            
            for row in reader:
                try:
                    # Extract data from row
                    email = row.get("email", "").strip()
                    name = row.get("name", "").strip()
                    college = row.get("college", "").strip()
                    skills = [s.strip() for s in row.get("skills", "").split(",") if s.strip()]
                    
                    # Validate required fields
                    if not email or not name:
                        result["errors"] += 1
                        result["error_details"].append(f"Missing required fields for row: {row}")
                        continue
                        
                    # Create user
                    user_id = self.create_user(email, name, "intern", skills, college)
                    if user_id:
                        result["success"] += 1
                    else:
                        result["errors"] += 1
                        result["error_details"].append(f"Failed to create user for row: {row}")
                except Exception as e:
                    result["errors"] += 1
                    result["error_details"].append(f"Error processing row: {row}, Error: {str(e)}")
            
            return result
        except Exception as e:
            print(f"Error importing interns from CSV: {str(e)}")
            return {
                "success": 0,
                "errors": 1,
                "error_details": [str(e)]
            }
            
    def get_performance_metrics(self, user_email: str, period: str = "weekly") -> dict:
        """
        Get performance metrics for a user
        
        Args:
            user_email: Email of the user
            period: Period for metrics (daily, weekly, monthly)
            
        Returns:
            Dictionary with performance metrics
        """
        def operation():
            # Get all tasks for the user
            tasks = self.get_user_tasks(user_email)
            
            # Get all progress records for the user
            progress_records = list(self.db.progress.find({
                "user_email": user_email
            }))
            
            # Calculate metrics
            total_tasks = len(tasks)
            completed_tasks = sum(1 for task in tasks if task["progress"]["status"] == "done")
            in_progress_tasks = sum(1 for task in tasks if task["progress"]["status"] == "in_progress")
            not_started_tasks = sum(1 for task in tasks if task["progress"]["status"] == "not_started")
            
            completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            
            # Calculate time-based metrics
            now = datetime.now()
            
            # Get date range based on period
            if period == "daily":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                days_in_period = 1
            elif period == "weekly":
                # Start of the week (Monday)
                start_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
                days_in_period = 7
            elif period == "monthly":
                # Start of the month
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                # Calculate days in the month
                next_month = now.replace(day=28) + timedelta(days=4)
                last_day = next_month - timedelta(days=next_month.day)
                days_in_period = last_day.day
            else:
                # Default to weekly
                start_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
                days_in_period = 7
                
            # Get tasks completed in the period
            tasks_completed_in_period = sum(1 for record in progress_records 
                                          if record.get("status") == "done" 
                                          and record.get("completion_date") 
                                          and record["completion_date"] >= start_date)
            
            # Calculate daily average
            daily_average = tasks_completed_in_period / days_in_period
            
            # Get attendance for the period
            attendance_records = self.get_attendance_history(user_email, days=days_in_period)
            
            # Calculate attendance metrics
            days_present = sum(1 for record in attendance_records if record["status"] == "Present")
            total_hours = sum(record["duration"] for record in attendance_records if record["duration"])
            
            attendance_rate = (days_present / days_in_period * 100) if days_in_period > 0 else 0
            avg_hours_per_day = (total_hours / days_present) if days_present > 0 else 0
            
            # Calculate productivity metrics
            productivity = (tasks_completed_in_period / total_hours) if total_hours > 0 else 0
            
            return {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "in_progress_tasks": in_progress_tasks,
                "not_started_tasks": not_started_tasks,
                "completion_rate": completion_rate,
                "tasks_completed_in_period": tasks_completed_in_period,
                "daily_average": daily_average,
                "days_present": days_present,
                "total_hours": total_hours,
                "attendance_rate": attendance_rate,
                "avg_hours_per_day": avg_hours_per_day,
                "productivity": productivity,
                "period": period,
                "days_in_period": days_in_period
            }
        
        try:
            # Execute with retry logic
            return self._execute_db_operation(operation)
        except Exception as e:
            print(f"Error getting performance metrics: {str(e)}")
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "in_progress_tasks": 0,
                "not_started_tasks": 0,
                "completion_rate": 0,
                "tasks_completed_in_period": 0,
                "daily_average": 0,
                "days_present": 0,
                "total_hours": 0,
                "attendance_rate": 0,
                "avg_hours_per_day": 0,
                "productivity": 0,
                "period": period,
                "days_in_period": 0
            }
            
    def get_leaderboard(self) -> List[dict]:
        """
        Get leaderboard data for all interns
        
        Returns:
            List of leaderboard entries
        """
        def operation():
            # Get all interns
            interns = self.get_users(role="intern")
            
            # Get all tasks
            all_tasks = list(self.db.tasks.find())
            total_tasks = len(all_tasks)
            
            # Get progress for each intern
            leaderboard = []
            for intern in interns:
                email = intern["email"]
                name = intern.get("name", email)
                
                # Get completed tasks
                completed_tasks = self.db.progress.count_documents({
                    "user_email": email,
                    "status": "done"
                })
                
                # Calculate completion rate
                completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                
                # Get performance metrics
                performance = self.get_performance_metrics(email, "weekly")
                
                leaderboard.append({
                    "email": email,
                    "name": name,
                    "completed_tasks": completed_tasks,
                    "total_tasks": total_tasks,
                    "completion_rate": completion_rate,
                    "productivity": performance["productivity"],
                    "attendance_rate": performance["attendance_rate"]
                })
                
            # Sort by completion rate (descending)
            leaderboard.sort(key=lambda x: x["completion_rate"], reverse=True)
            
            # Add position
            for i, entry in enumerate(leaderboard):
                entry["position"] = i + 1
                
            return leaderboard
        
        try:
            # Execute with retry logic
            return self._execute_db_operation(operation)
        except Exception as e:
            print(f"Error getting leaderboard: {str(e)}")
            return []
            
    def get_task_categories(self) -> List[dict]:
        """
        Get all task categories
        
        Returns:
            List of task categories
        """
        def operation():
            try:
                # Get categories from database
                categories = list(self.db.task_categories.find().sort("name", 1))
                
                # If no categories exist, create default ones
                if not categories:
                    default_categories = [
                        {"name": "General", "description": "General tasks", "color": "#1E88E5"},
                        {"name": "Technical", "description": "Technical tasks", "color": "#43A047"},
                        {"name": "Soft Skills", "description": "Soft skills development", "color": "#FB8C00"}
                    ]
                    
                    for category in default_categories:
                        self.db.task_categories.insert_one(category)
                    
                    # Get the newly created categories
                    categories = list(self.db.task_categories.find().sort("name", 1))
                
                # Convert ObjectId to string
                for category in categories:
                    if "_id" in category:
                        category["_id"] = str(category["_id"])
                
                return categories
            except Exception as e:
                print(f"Error in get_task_categories operation: {str(e)}")
                # Return default categories if none exist
                return [
                    {"_id": "default", "name": "General", "description": "General tasks", "color": "#1E88E5"},
                    {"_id": "technical", "name": "Technical", "description": "Technical tasks", "color": "#43A047"},
                    {"_id": "soft_skills", "name": "Soft Skills", "description": "Soft skills development", "color": "#FB8C00"}
                ]
        
        try:
            # Execute with retry logic
            result = self._execute_db_operation(operation)
            
            # Validate the result
            if not isinstance(result, list):
                print(f"Invalid result type from get_task_categories: {type(result)}")
                return [
                    {"_id": "default", "name": "General", "description": "General tasks", "color": "#1E88E5"},
                    {"_id": "technical", "name": "Technical", "description": "Technical tasks", "color": "#43A047"},
                    {"_id": "soft_skills", "name": "Soft Skills", "description": "Soft skills development", "color": "#FB8C00"}
                ]
                
            return result
        except Exception as e:
            print(f"Error getting task categories: {str(e)}")
            return [
                {"_id": "default", "name": "General", "description": "General tasks", "color": "#1E88E5"},
                {"_id": "technical", "name": "Technical", "description": "Technical tasks", "color": "#43A047"},
                {"_id": "soft_skills", "name": "Soft Skills", "description": "Soft skills development", "color": "#FB8C00"}
            ]
            
    def add_task_category(self, name: str, description: str, color: str = "#1E88E5") -> str:
        """
        Add a new task category
        
        Args:
            name: Name of the category
            description: Description of the category
            color: Color code for the category (hex)
            
        Returns:
            ID of the created category
        """
        def operation():
            try:
                # Check if category already exists
                existing = self.db.task_categories.find_one({"name": name})
                if existing:
                    return str(existing["_id"])
                
                # Create new category
                category = {
                    "name": name,
                    "description": description,
                    "color": color,
                    "created_at": datetime.now()
                }
                
                result = self.db.task_categories.insert_one(category)
                return str(result.inserted_id)
            except Exception as e:
                print(f"Error in add_task_category operation: {str(e)}")
                return None
        
        try:
            # Execute with retry logic
            return self._execute_db_operation(operation)
        except Exception as e:
            print(f"Error adding task category: {str(e)}")
            return None
            
    def update_task_category(self, category_id: str, name: str = None, 
                           description: str = None, color: str = None) -> bool:
        """
        Update a task category
        
        Args:
            category_id: ID of the category
            name: New name for the category
            description: New description for the category
            color: New color for the category
            
        Returns:
            True if successful, False otherwise
        """
        def operation():
            try:
                # Create update data with only provided fields
                update_data = {}
                if name is not None:
                    update_data["name"] = name
                if description is not None:
                    update_data["description"] = description
                if color is not None:
                    update_data["color"] = color
                
                # If no fields to update, return success
                if not update_data:
                    return True
                
                # Update the category
                result = self.db.task_categories.update_one(
                    {"_id": ObjectId(category_id)},
                    {"$set": update_data}
                )
                
                return result.modified_count > 0
            except Exception as e:
                print(f"Error in update_task_category operation: {str(e)}")
                return False
        
        try:
            # Execute with retry logic
            return self._execute_db_operation(operation)
        except Exception as e:
            print(f"Error updating task category: {str(e)}")
            return False
            
    def delete_task_category(self, category_id: str) -> bool:
        """
        Delete a task category
        
        Args:
            category_id: ID of the category
            
        Returns:
            True if successful, False otherwise
        """
        def operation():
            try:
                # Check if category is in use
                tasks_using_category = self.db.tasks.count_documents({"category": category_id})
                if tasks_using_category > 0:
                    print(f"Cannot delete category: {tasks_using_category} tasks are using it")
                    return False
                
                # Delete the category
                result = self.db.task_categories.delete_one({"_id": ObjectId(category_id)})
                return result.deleted_count > 0
            except Exception as e:
                print(f"Error in delete_task_category operation: {str(e)}")
                return False
        
        try:
            # Execute with retry logic
            return self._execute_db_operation(operation)
        except Exception as e:
            print(f"Error deleting task category: {str(e)}")
            return False