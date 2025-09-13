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
        """Create a ticket using ticket service"""
        
        title = params.get("title")
        description = params.get("description")
        priority = params.get("priority", "medium")
        
        # Use ticket service
        from backend.services.ticket_service import ticket_service
        ticket = ticket_service.create_ticket(
            title=title,
            description=description,
            created_by=user_context.user_id,
            priority=priority
        )
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data=ticket.to_dict(),
            message=f"Created ticket {ticket.id}: {title}"
        )