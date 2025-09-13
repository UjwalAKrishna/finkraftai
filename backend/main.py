# Simple FastAPI backend

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from backend.tools.base_tool import UserContext
from backend.core.tool_registry import registry
from backend.core.memory_aware_agent import memory_aware_agent
from backend.core.planning_engine import planning_engine
from backend.core.tool_registry import registry
from backend.routers.tickets import router as tickets_router
from backend.routers.admin import router as admin_router

app = FastAPI(title="FinkraftAI Backend", version="1.0.0")

# Include routers
app.include_router(tickets_router)
app.include_router(admin_router)

# Simple request models
class MessageRequest(BaseModel):
    user_id: str
    tool_name: str
    params: Dict[str, Any]

class TicketRequest(BaseModel):
    user_id: str
    title: str
    description: str
    priority: str = "medium"

class UpdateTicketRequest(BaseModel):
    user_id: str
    ticket_id: str
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    action: Optional[str] = None

class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: str = None

@app.get("/")
def root():
    """Simple health check"""
    return {"message": "FinkraftAI Backend is running", "status": "ok"}

@app.post("/execute_tool")
def execute_tool(request: MessageRequest):
    """Execute a tool with parameters"""
    
    try:
        # Create user context
        user_context = UserContext(user_id=request.user_id)
        
        # Execute tool through registry
        result = registry.execute_tool(
            tool_name=request.tool_name,
            params=request.params,
            user_context=user_context
        )
        
        return {
            "status": result.status,
            "message": result.message,
            "data": result.data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{user_id}/permissions")
def get_user_permissions(user_id: str):
    """Get user permissions and allowed tools"""
    
    try:
        summary = registry.get_user_summary(user_id)
        return summary
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/user/{user_id}/tools")
def get_user_tools(user_id: str):
    """Get tools available to user"""
    
    try:
        tools_info = registry.get_available_tools_info(user_id)
        return {"tools": tools_info}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tickets/create")
def create_ticket(request: TicketRequest):
    """Create a new ticket"""
    
    try:
        user_context = UserContext(user_id=request.user_id)
        
        result = registry.execute_tool("create_ticket", {
            "title": request.title,
            "description": request.description,
            "priority": request.priority
        }, user_context)
        
        return {
            "status": result.status,
            "message": result.message,
            "ticket": result.data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tickets/{user_id}")
def get_tickets(user_id: str, status: Optional[str] = None):
    """Get user's tickets"""
    
    try:
        user_context = UserContext(user_id=user_id)
        
        params = {}
        if status:
            params["status"] = status
            
        result = registry.execute_tool("view_tickets", params, user_context)
        
        return {
            "status": result.status,
            "message": result.message,
            "tickets": result.data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/tickets/update")
def update_ticket(request: UpdateTicketRequest):
    """Update a ticket"""
    
    try:
        user_context = UserContext(user_id=request.user_id)
        
        params = {"ticket_id": request.ticket_id}
        if request.status:
            params["status"] = request.status
        if request.assigned_to:
            params["assigned_to"] = request.assigned_to
        if request.action:
            params["action"] = request.action
            
        result = registry.execute_tool("update_ticket", params, user_context)
        
        return {
            "status": result.status,
            "message": result.message,
            "ticket": result.data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
def chat_with_agent(request: ChatRequest):
    """Chat with the AI agent using natural language"""
    
    try:
        # Create user context
        user_context = UserContext(user_id=request.user_id)
        
        # Process message through memory-aware agent
        response = memory_aware_agent.process_message(request.message, user_context, request.session_id if hasattr(request, 'session_id') else None)
        
        return {
            "user_message": request.message,
            "agent_response": response["message"],
            "success": response["success"],
            "tool_used": response.get("tool_used"),
            "parameters": response.get("parameters"),
            "confidence": response.get("confidence"),
            "suggestions": response.get("suggestions", []),
            "llm_response": response.get("llm_response", {}),
            "memory_context": response.get("memory_context", {}),
            "thread_id": response.get("thread_id")
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory/{user_id}/search")
def search_memory(user_id: str, query: str, limit: int = 10):
    """Search user's conversation memory"""
    
    try:
        results = memory_aware_agent.search_conversation_history(user_id, query, limit)
        return {"results": results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory/{user_id}/threads")
def get_conversation_threads(user_id: str):
    """Get user's conversation threads"""
    
    try:
        threads = memory_aware_agent.get_conversation_threads(user_id)
        return {"threads": threads}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/{user_id}/threads/{thread_id}/activate")
def activate_thread(user_id: str, thread_id: str):
    """Switch to a specific conversation thread"""
    
    try:
        success = memory_aware_agent.switch_conversation_thread(user_id, thread_id)
        return {"success": success, "message": f"Switched to thread {thread_id}" if success else "Thread not found"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory/{user_id}/insights")
def get_memory_insights(user_id: str):
    """Get user's memory insights and patterns"""
    
    try:
        insights = memory_aware_agent.get_memory_insights(user_id)
        return insights
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/plans/create")
def create_execution_plan(request: dict):
    """Create an execution plan for complex workflows"""
    
    try:
        user_id = request.get("user_id")
        goal = request.get("goal")
        template_name = request.get("template_name")
        custom_params = request.get("custom_params", {})
        
        user_context = UserContext(user_id=user_id)
        
        plan = planning_engine.create_plan(
            goal=goal,
            user_context=user_context,
            template_name=template_name,
            custom_params=custom_params
        )
        
        return {
            "success": True,
            "plan_id": plan.plan_id,
            "goal": plan.goal,
            "description": plan.description,
            "steps": len(plan.steps),
            "approval_required": plan.approval_required
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/plans/{plan_id}/execute")
def execute_plan(plan_id: str, user_id: str):
    """Execute an approved plan"""
    
    try:
        user_context = UserContext(user_id=user_id)
        result = planning_engine.execute_plan_sync(plan_id, user_context)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/plans/{plan_id}/status")
def get_plan_status(plan_id: str):
    """Get plan execution status"""
    
    try:
        status = planning_engine.get_plan_status(plan_id)
        return status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/plans/user/{user_id}")
def get_user_plans(user_id: str, limit: int = 20):
    """Get user's execution plans"""
    
    try:
        plans = planning_engine.get_user_plans(user_id, limit)
        return {"plans": plans}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/plans/templates")
def get_plan_templates():
    """Get available plan templates"""
    
    try:
        templates = {}
        for name, template in planning_engine.business_templates.items():
            templates[name] = {
                "description": template.get("description", ""),
                "steps": len(template.get("steps", [])),
                "approval_required": template.get("approval_required", False),
                "keywords": template.get("keywords", [])
            }
        
        return {"templates": templates}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)