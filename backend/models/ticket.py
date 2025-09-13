# Simple ticket models

from typing import Optional, List
from datetime import datetime


class Ticket:
    """Simple ticket model"""
    
    def __init__(self, id: str = None, title: str = "", description: str = "", 
                 status: str = "open", priority: str = "medium", 
                 created_by: str = "", assigned_to: str = None,
                 created_at: str = None, updated_at: str = None):
        self.id = id
        self.title = title
        self.description = description
        self.status = status  # open, in_progress, closed
        self.priority = priority  # low, medium, high
        self.created_by = created_by
        self.assigned_to = assigned_to
        self.created_at = created_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.updated_at = updated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "created_by": self.created_by,
            "assigned_to": self.assigned_to,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(**data)