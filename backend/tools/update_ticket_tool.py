# Simple update ticket tool

from typing import Dict, Any, List
from .base_tool import BaseTool, ToolResult, ToolResultStatus, UserContext, ToolParameter


class UpdateTicketTool(BaseTool):
    """Simple tool for updating tickets"""
    
    @property
    def name(self) -> str:
        return "update_ticket"
    
    @property
    def description(self) -> str:
        return "Update ticket status, assign, or close ticket"
    
    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="ticket_id",
                type="string",
                required=True,
                description="Ticket ID to update"
            ),
            ToolParameter(
                name="status",
                type="string",
                required=False,
                description="New status (open, in_progress, closed)"
            ),
            ToolParameter(
                name="assigned_to",
                type="string",
                required=False,
                description="Assign ticket to user"
            ),
            ToolParameter(
                name="action",
                type="string",
                required=False,
                description="Quick action (close, assign)"
            )
        ]
    
    def execute(self, params: Dict[str, Any], user_context: UserContext) -> ToolResult:
        """Update a ticket"""
        
        ticket_id = params.get("ticket_id")
        status = params.get("status")
        assigned_to = params.get("assigned_to")
        action = params.get("action")
        
        from backend.services.ticket_service import ticket_service
        
        # Handle quick actions
        if action == "close":
            ticket = ticket_service.close_ticket(ticket_id)
            message = f"Closed ticket {ticket_id}"
        elif action == "assign" and assigned_to:
            ticket = ticket_service.assign_ticket(ticket_id, assigned_to)
            message = f"Assigned ticket {ticket_id} to {assigned_to}"
        else:
            # Regular update
            updates = {}
            if status:
                updates["status"] = status
            if assigned_to:
                updates["assigned_to"] = assigned_to
            
            ticket = ticket_service.update_ticket(ticket_id, **updates)
            message = f"Updated ticket {ticket_id}"
        
        if not ticket:
            return ToolResult(
                status=ToolResultStatus.ERROR,
                message=f"Ticket {ticket_id} not found"
            )
        
        return ToolResult(
            status=ToolResultStatus.SUCCESS,
            data=ticket.to_dict(),
            message=message
        )