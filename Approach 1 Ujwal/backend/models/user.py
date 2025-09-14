# User, session, and workspace models

from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    """User model"""
    user_id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    workspace_id: str = "default"
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "workspace_id": self.workspace_id,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(**data)


@dataclass
class Session:
    """User session model"""
    session_id: str
    user_id: str
    workspace_id: str = "default"
    started_at: Optional[str] = None
    last_activity: Optional[str] = None
    is_active: bool = True
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "workspace_id": self.workspace_id,
            "started_at": self.started_at,
            "last_activity": self.last_activity,
            "is_active": self.is_active
        }


@dataclass
class Workspace:
    """Workspace model"""
    workspace_id: str
    name: str
    description: Optional[str] = None
    created_by: str = ""
    is_active: bool = True
    created_at: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "workspace_id": self.workspace_id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "is_active": self.is_active,
            "created_at": self.created_at
        }