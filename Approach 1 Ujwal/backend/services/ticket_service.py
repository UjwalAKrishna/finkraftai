# Database-driven ticket service

import time
from typing import List, Optional
from backend.models.ticket import Ticket
from database.repositories.ticket_repo import ticket_repo


class TicketService:
    """Database-driven ticket service"""
    
    def __init__(self):
        # Get next available ID from database
        from database.connection import db_manager
        try:
            result = db_manager.execute_query(
                "SELECT MAX(CAST(SUBSTR(ticket_id, 5) AS INTEGER)) FROM tickets",
                fetch_one=True
            )
            last_id = result[0] if result and result[0] else 0
            self._next_id = last_id + 1
        except:
            self._next_id = 1
    
    def create_ticket(self, title: str, description: str, created_by: str, 
                     priority: str = "medium") -> Ticket:
        """Create a new ticket"""
        ticket_id = f"TIC-{self._next_id:04d}"
        self._next_id += 1
        
        ticket = Ticket(
            id=ticket_id,
            title=title,
            description=description,
            created_by=created_by,
            priority=priority
        )
        
        # Save to database
        ticket_repo.create_ticket(ticket)
        return ticket
    
    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Get ticket by ID"""
        return ticket_repo.get_ticket(ticket_id)
    
    def get_tickets(self, user_id: str = None, status: str = None) -> List[Ticket]:
        """Get all tickets with optional filters"""
        return ticket_repo.get_tickets(user_id=user_id, status=status)
    
    def update_ticket(self, ticket_id: str, **updates) -> Optional[Ticket]:
        """Update ticket fields"""
        success = ticket_repo.update_ticket(ticket_id, **updates)
        if success:
            return self.get_ticket(ticket_id)
        return None
    
    def assign_ticket(self, ticket_id: str, assigned_to: str) -> Optional[Ticket]:
        """Assign ticket to user"""
        return self.update_ticket(ticket_id, assigned_to=assigned_to, status="in_progress")
    
    def close_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Close a ticket"""
        return self.update_ticket(ticket_id, status="closed")
    
    def get_user_tickets(self, user_id: str) -> dict:
        """Get user's ticket summary"""
        tickets = self.get_tickets(user_id=user_id)
        
        return {
            "total": len(tickets),
            "open": len([t for t in tickets if t.status == "open"]),
            "in_progress": len([t for t in tickets if t.status == "in_progress"]),
            "closed": len([t for t in tickets if t.status == "closed"]),
            "tickets": [t.to_dict() for t in tickets]
        }

# Global service instance
ticket_service = TicketService()