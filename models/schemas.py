from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field

class Resource(BaseModel):
    title: str
    url: str
    type: str = "link"  # link, document, video, etc.
    description: Optional[str] = None

class TaskCategory(BaseModel):
    name: str
    description: Optional[str] = None
    color: str = "#1f77b4"  # Default color for visualization

class Task(BaseModel):
    title: str
    description: str
    category: str
    resources: List[Resource]
    assigned_to: str
    deadline: Optional[datetime] = None
    prerequisites: List[str] = []  # List of task IDs that must be completed first
    weight: int = 1  # Task importance/complexity weight
    tags: List[str] = []
    estimated_hours: Optional[float] = None
    
class Progress(BaseModel):
    user_email: str
    task_id: str
    status: str = "not_started"  # not_started, in_progress, done
    submission_link: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=datetime.now)
    time_spent: Optional[float] = None  # Hours spent on task
    notes: Optional[str] = None
    review_status: Optional[str] = None  # pending, approved, needs_work
    reviewer_comments: Optional[str] = None

class UserProfile(BaseModel):
    email: str
    role: str
    name: Optional[str] = None
    skills: List[str] = []
    joined_date: datetime = Field(default_factory=datetime.now)
    performance_metrics: Dict = Field(default_factory=dict)
    preferences: Dict = Field(default_factory=dict)

class PerformanceMetrics(BaseModel):
    user_email: str
    period: str  # daily, weekly, monthly
    date: datetime
    tasks_completed: int = 0
    on_time_completion_rate: float = 0.0
    average_task_time: float = 0.0
    productivity_score: float = 0.0
    streak_days: int = 0
