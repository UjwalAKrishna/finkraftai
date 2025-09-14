# Simple base tool - minimal implementation

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from enum import Enum


class ToolResultStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    PERMISSION_DENIED = "permission_denied"


class ToolResult:
    """Simple result format for tool executions"""
    def __init__(self, status: ToolResultStatus, message: str, data: Dict[str, Any] = None):
        self.status = status
        self.message = message
        self.data = data or {}


class UserContext:
    """User context with database-driven permissions"""
    def __init__(self, user_id: str, workspace_id: str = "default", session_id: str = "default"):
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.session_id = session_id
        
        # Load permissions from database
        from database.repositories.permission_repo import permission_repo
        self.permissions = permission_repo.get_user_permissions(user_id)
        self.groups = permission_repo.get_user_groups(user_id)
        self.can_see_traces = permission_repo.can_see_traces(user_id)
        self.user_info = permission_repo.get_user_info(user_id)
        
        # Set primary role (first group or default)
        self.role = self.groups[0] if self.groups else "Viewer"


class ToolParameter:
    """Simple tool parameter definition"""
    def __init__(self, name: str, type: str, required: bool = True, description: str = "", default: Any = None):
        self.name = name
        self.type = type
        self.required = required
        self.description = description
        self.default = default


class BaseTool(ABC):
    """Simple base class for all tools"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description"""
        pass
    
    @abstractmethod
    def get_parameters(self) -> List[ToolParameter]:
        """Get tool parameters"""
        pass
    
    @abstractmethod
    def execute(self, params: Dict[str, Any], user_context: UserContext) -> ToolResult:
        """Execute the tool"""
        pass