# Simple tool registry - loads tools and permissions from config

import json
import os
from typing import Dict, List, Optional
from backend.tools import get_tool, get_all_tools
from backend.tools.base_tool import UserContext

class ToolRegistry:
    """Simple registry for managing tools and permissions"""
    
    def __init__(self):
        self.tools_config = self._load_config("config/actions.json")
        self.roles_config = self._load_config("config/roles.json")
        
    def _load_config(self, file_path: str) -> dict:
        """Load JSON config file"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def get_allowed_tools(self, role: str) -> List[str]:
        """Get list of tools allowed for a role"""
        for role_config in self.roles_config.get("roles", []):
            if role_config["name"] == role:
                return role_config.get("permissions", [])
        return []
    
    def can_use_tool(self, tool_name: str, role: str) -> bool:
        """Check if role can use a specific tool"""
        allowed_tools = self.get_allowed_tools(role)
        return tool_name in allowed_tools
    
    def can_see_traces(self, role: str) -> bool:
        """Check if role can see execution traces"""
        for role_config in self.roles_config.get("roles", []):
            if role_config["name"] == role:
                return role_config.get("can_see_traces", False)
        return False
    
    def execute_tool(self, tool_name: str, params: dict, user_context: UserContext):
        """Execute a tool with permission checking"""
        
        # Check permissions
        if not self.can_use_tool(tool_name, user_context.role):
            from backend.tools.base_tool import ToolResult, ToolResultStatus
            return ToolResult(
                status=ToolResultStatus.PERMISSION_DENIED,
                message=f"Role '{user_context.role}' not allowed to use tool '{tool_name}'"
            )
        
        # Get and execute tool
        try:
            tool = get_tool(tool_name)
            return tool.execute(params, user_context)
        except ValueError as e:
            from backend.tools.base_tool import ToolResult, ToolResultStatus
            return ToolResult(
                status=ToolResultStatus.ERROR,
                message=str(e)
            )
    
    def get_available_roles(self) -> List[str]:
        """Get list of all available roles"""
        return [role["name"] for role in self.roles_config.get("roles", [])]

# Global registry instance
registry = ToolRegistry()