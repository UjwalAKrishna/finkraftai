# Simple view tickets tool

from typing import Dict, Any, List
from .base_tool import BaseTool, ToolResult, ToolResultStatus, UserContext, ToolParameter


class ViewTicketsTool(BaseTool):
    """Simple tool for viewing tickets"""
    
    @property
    def name(self) -> str:
        return "view_tickets"
    
    @property
    def description(self) -> str:
        return "View your tickets with optional status filter"
    
    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="status",
                type="string",
                required=False,
                description="Filter by status (open, in_progress, closed)"
            )
        ]
    
    def execute(self, params: Dict[str, Any], user_context: UserContext) -> ToolResult:
        """View tickets for user"""
        
        status = params.get("status")
        
        from backend.services.ticket_service import ticket_service
        user_tickets = ticket_service.get_user_tickets(user_context.user_id)
        
        # Filter by status if provided
        if status:
            filtered_tickets = [t for t in user_tickets["tickets"] if t["status"] == status]
            user_tickets["filtered"] = filtered_tickets
            user_tickets["filtered_count"] = len(filtered_tickets)
            message = f"Found {len(filtered_tickets)} {status} tickets"
        else:
            message = f"Found {user_tickets['total']} total tickets"
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data=user_tickets,
            message=message
        )