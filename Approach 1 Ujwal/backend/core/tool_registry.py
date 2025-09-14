# Database-driven tool registry

from typing import Dict, List, Optional
from backend.tools import get_tool, get_all_tools
from backend.tools.base_tool import UserContext
from database.repositories.permission_repo import permission_repo


class ToolRegistry:
    """Database-driven registry for managing tools and permissions"""
    
    def __init__(self):
        # Load available tools from the tools module
        self.available_tools = get_all_tools()
        
    def get_allowed_tools(self, user_id: str) -> List[str]:
        """Get list of tools allowed for a user based on database permissions"""
        user_permissions = permission_repo.get_user_permissions(user_id)
        
        # Filter available tools by user permissions
        allowed_tools = []
        for tool_name in self.available_tools.keys():
            if tool_name in user_permissions:
                allowed_tools.append(tool_name)
        
        return allowed_tools
    
    def can_use_tool(self, tool_name: str, user_id: str) -> bool:
        """Check if user can use a specific tool"""
        allowed_tools = self.get_allowed_tools(user_id)
        return tool_name in allowed_tools
    
    def can_see_traces(self, user_id: str) -> bool:
        """Check if user can see execution traces"""
        return permission_repo.can_see_traces(user_id)
    
    def execute_tool(self, tool_name: str, params: dict, user_context: UserContext):
        """Execute a tool with permission checking"""
        
        # Check permissions
        if not self.can_use_tool(tool_name, user_context.user_id):
            from backend.tools.base_tool import ToolResult, ToolResultStatus
            return ToolResult(
                status=ToolResultStatus.PERMISSION_DENIED,
                message=f"User '{user_context.user_id}' not allowed to use tool '{tool_name}'"
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
    
    def get_user_summary(self, user_id: str) -> dict:
        """Get user permission summary"""
        user_info = permission_repo.get_user_info(user_id)
        if not user_info:
            return {"error": "User not found"}
        
        return {
            "user_info": user_info,
            "groups": permission_repo.get_user_groups(user_id),
            "permissions": permission_repo.get_user_permissions(user_id),
            "allowed_tools": self.get_allowed_tools(user_id),
            "can_see_traces": self.can_see_traces(user_id)
        }
    
    def get_available_tools_info(self, user_id: str) -> List[dict]:
        """Get information about tools available to user"""
        allowed_tools = self.get_allowed_tools(user_id)
        
        tools_info = []
        for tool_name in allowed_tools:
            if tool_name in self.available_tools:
                tool = self.available_tools[tool_name]
                tools_info.append({
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": [
                        {
                            "name": p.name,
                            "type": p.type,
                            "required": p.required,
                            "description": p.description
                        }
                        for p in tool.get_parameters()
                    ]
                })
        
        return tools_info

# Global registry instance
registry = ToolRegistry()