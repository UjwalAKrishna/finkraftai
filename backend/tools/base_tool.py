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
    """Simple user context"""
    def __init__(self, user_id: str, role: str, workspace_id: str = "default", session_id: str = "default", permissions: List[str] = None):
        self.user_id = user_id
        self.role = role
        self.workspace_id = workspace_id
        self.session_id = session_id
        self.permissions = permissions or []


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