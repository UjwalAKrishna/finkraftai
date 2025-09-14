# Ticket repository - database operations for tickets

from typing import List, Optional, Dict
from database.connection import db_manager
from backend.models.ticket import Ticket
import time


class TicketRepository:
    """Repository for ticket database operations"""
    
    def create_ticket(self, ticket: Ticket) -> str:
        """Create a new ticket in database"""
        
        query = """
        INSERT INTO tickets (ticket_id, title, description, status, priority, 
                           created_by, assigned_to, workspace_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        db_manager.execute_query(query, (
            ticket.id, ticket.title, ticket.description, ticket.status,
            ticket.priority, ticket.created_by, ticket.assigned_to, "default"
        ))
        
        return ticket.id
    
    def get_ticket(self, ticket_id: str) -> Optional[Ticket]:
        """Get ticket by ID"""
        
        query = """
        SELECT ticket_id, title, description, status, priority,
               created_by, assigned_to, created_at, updated_at
        FROM tickets 
        WHERE ticket_id = ?
        """
        
        result = db_manager.execute_query(query, (ticket_id,), fetch_one=True)
        
        if result:
            return Ticket(
                id=result['ticket_id'],
                title=result['title'],
                description=result['description'],
                status=result['status'],
                priority=result['priority'],
                created_by=result['created_by'],
                assigned_to=result['assigned_to'],
                created_at=result['created_at'],
                updated_at=result['updated_at']
            )
        return None
    
    def get_tickets(self, user_id: str = None, status: str = None, 
                   workspace_id: str = "default") -> List[Ticket]:
        """Get tickets with optional filters"""
        
        query = """
        SELECT ticket_id, title, description, status, priority,
               created_by, assigned_to, created_at, updated_at
        FROM tickets 
        WHERE workspace_id = ?
        """
        params = [workspace_id]
        
        if user_id:
            query += " AND (created_by = ? OR assigned_to = ?)"
            params.extend([user_id, user_id])
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        query += " ORDER BY created_at DESC"
        
        rows = db_manager.execute_query(query, tuple(params))
        
        tickets = []
        for row in rows:
            tickets.append(Ticket(
                id=row['ticket_id'],
                title=row['title'],
                description=row['description'],
                status=row['status'],
                priority=row['priority'],
                created_by=row['created_by'],
                assigned_to=row['assigned_to'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            ))
        
        return tickets
    
    def update_ticket(self, ticket_id: str, **updates) -> bool:
        """Update ticket fields"""
        
        if not updates:
            return False
        
        # Build dynamic update query
        set_clauses = []
        params = []
        
        allowed_fields = ['title', 'description', 'status', 'priority', 'assigned_to']
        
        for field, value in updates.items():
            if field in allowed_fields:
                set_clauses.append(f"{field} = ?")
                params.append(value)
        
        if not set_clauses:
            return False
        
        # Always update timestamp
        set_clauses.append("updated_at = ?")
        params.append(time.strftime("%Y-%m-%d %H:%M:%S"))
        
        params.append(ticket_id)
        
        query = f"""
        UPDATE tickets 
        SET {', '.join(set_clauses)}
        WHERE ticket_id = ?
        """
        
        try:
            db_manager.execute_query(query, tuple(params))
            return True
        except Exception:
            return False

# Global repository instance
ticket_repo = TicketRepository()