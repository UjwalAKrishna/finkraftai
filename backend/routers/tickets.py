# Ticket management REST API endpoints

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from backend.tools.base_tool import UserContext
from backend.core.tool_registry import registry

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


class CreateTicketRequest(BaseModel):
    user_id: str
    title: str
    description: str
    priority: str = "medium"


class UpdateTicketRequest(BaseModel):
    user_id: str
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    priority: Optional[str] = None


@router.post("/")
def create_ticket(request: CreateTicketRequest):
    """Create a new ticket"""
    
    try:
        user_context = UserContext(user_id=request.user_id)
        
        result = registry.execute_tool("create_ticket", {
            "title": request.title,
            "description": request.description,
            "priority": request.priority
        }, user_context)
        
        if result.status == "success":
            return {
                "success": True,
                "ticket": result.data,
                "message": result.message
            }
        else:
            raise HTTPException(status_code=400, detail=result.message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}")
def get_user_tickets(user_id: str, status: Optional[str] = None):
    """Get user's tickets"""
    
    try:
        user_context = UserContext(user_id=user_id)
        
        params = {}
        if status:
            params["status"] = status
            
        result = registry.execute_tool("view_tickets", params, user_context)
        
        if result.status == "success":
            return {
                "success": True,
                "tickets": result.data,
                "message": result.message
            }
        else:
            raise HTTPException(status_code=400, detail=result.message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{ticket_id}")
def update_ticket(ticket_id: str, request: UpdateTicketRequest):
    """Update a ticket"""
    
    try:
        user_context = UserContext(user_id=request.user_id)
        
        params = {"ticket_id": ticket_id}
        if request.status:
            params["status"] = request.status
        if request.assigned_to:
            params["assigned_to"] = request.assigned_to
        if request.priority:
            params["priority"] = request.priority
            
        result = registry.execute_tool("update_ticket", params, user_context)
        
        if result.status == "success":
            return {
                "success": True,
                "ticket": result.data,
                "message": result.message
            }
        else:
            raise HTTPException(status_code=400, detail=result.message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ticket_id}/close")
def close_ticket(ticket_id: str, user_id: str):
    """Close a ticket"""
    
    try:
        user_context = UserContext(user_id=user_id)
        
        result = registry.execute_tool("update_ticket", {
            "ticket_id": ticket_id,
            "action": "close"
        }, user_context)
        
        if result.status == "success":
            return {
                "success": True,
                "ticket": result.data,
                "message": result.message
            }
        else:
            raise HTTPException(status_code=400, detail=result.message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ticket_id}/assign")
def assign_ticket(ticket_id: str, user_id: str, assigned_to: str):
    """Assign a ticket to someone"""
    
    try:
        user_context = UserContext(user_id=user_id)
        
        result = registry.execute_tool("update_ticket", {
            "ticket_id": ticket_id,
            "action": "assign",
            "assigned_to": assigned_to
        }, user_context)
        
        if result.status == "success":
            return {
                "success": True,
                "ticket": result.data,
                "message": result.message
            }
        else:
            raise HTTPException(status_code=400, detail=result.message)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))