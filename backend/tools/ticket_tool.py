# Simple ticket tool - basic implementation

from typing import Dict, Any, List
from .base_tool import BaseTool, ToolResult, ToolResultStatus, UserContext, ToolParameter
import time


class TicketTool(BaseTool):
    """Simple tool for creating support tickets"""
    
    @property
    def name(self) -> str:
        return "create_ticket"
    
    @property
    def description(self) -> str:
        return "Create a support ticket with title and description"
    
    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="title",
                type="string",
                required=True,
                description="Ticket title/summary"
            ),
            ToolParameter(
                name="description",
                type="string",
                required=True,
                description="Detailed ticket description"
            ),
            ToolParameter(
                name="priority",
                type="string",
                required=False,
                description="Ticket priority (low, medium, high)",
                default="medium"
            )
        ]
    
    def execute(self, params: Dict[str, Any], user_context: UserContext) -> ToolResult:
        """Simple mock implementation that creates a ticket"""
        
        title = params.get("title")
        description = params.get("description")
        priority = params.get("priority", "medium")
        
        # Mock ticket creation
        ticket_id = f"TIC-{int(time.time()) % 10000}"
        
        mock_result = {
            "ticket_id": ticket_id,
            "title": title,
            "description": description,
            "priority": priority,
            "status": "open",
            "created_by": user_context.user_id,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data=mock_result,
            message=f"Created ticket {ticket_id}: {title}"
        )