# Conversation and message models

from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConversationMessage:
    """Individual conversation message"""
    id: Optional[int] = None
    thread_id: str = ""
    user_id: str = ""
    role: str = ""  # 'user' or 'assistant'
    message: str = ""
    message_type: str = "text"  # text, tool_call, tool_result, system
    tool_name: Optional[str] = None
    tool_parameters: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    workspace_id: str = "default"
    timestamp: Optional[str] = None
    importance_score: float = 0.5
    tokens_used: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "role": self.role,
            "message": self.message,
            "message_type": self.message_type,
            "tool_name": self.tool_name,
            "tool_parameters": self.tool_parameters,
            "tool_result": self.tool_result,
            "session_id": self.session_id,
            "workspace_id": self.workspace_id,
            "timestamp": self.timestamp,
            "importance_score": self.importance_score,
            "tokens_used": self.tokens_used
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(**data)


@dataclass
class ConversationThread:
    """Conversation thread grouping related messages"""
    id: Optional[int] = None
    thread_id: str = ""
    user_id: str = ""
    title: str = ""
    description: Optional[str] = None
    started_at: Optional[str] = None
    last_activity: Optional[str] = None
    is_active: bool = True
    workspace_id: str = "default"
    thread_type: str = "general"  # general, investigation, project, support
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "started_at": self.started_at,
            "last_activity": self.last_activity,
            "is_active": self.is_active,
            "workspace_id": self.workspace_id,
            "thread_type": self.thread_type
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(**data)


@dataclass
class ConversationSummary:
    """Summary of conversation thread"""
    id: Optional[int] = None
    thread_id: str = ""
    summary_text: str = ""
    summary_type: str = "auto"  # auto, manual, key_points
    start_message_id: Optional[int] = None
    end_message_id: Optional[int] = None
    created_at: Optional[str] = None
    token_count: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "summary_text": self.summary_text,
            "summary_type": self.summary_type,
            "start_message_id": self.start_message_id,
            "end_message_id": self.end_message_id,
            "created_at": self.created_at,
            "token_count": self.token_count
        }