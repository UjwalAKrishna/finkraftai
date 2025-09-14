# Simple FastAPI backend

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from backend.tools.base_tool import UserContext
from backend.core.tool_registry import registry
from backend.core.memory_aware_agent import memory_aware_agent
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

@app.get("/api/download/{filename}")
def download_file(filename: str):
    """Download exported files"""
    import os
    from fastapi.responses import FileResponse
    
    try:
        file_path = os.path.join("exports", filename)
        if os.path.exists(file_path):
            return FileResponse(
                path=file_path,
                filename=filename,
                media_type='application/octet-stream'
            )
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        
        # Get detailed trace information if available
        trace_details = None
        if response.get("trace_id"):
            from backend.services.trace_service import trace_service
            trace_details = trace_service.get_trace(response["trace_id"])
        
        return {
            "user_message": request.message,
            "agent_response": response["message"],
            "success": response["success"],
            "tool_used": response.get("tool_used"),
            "trace_id": response.get("trace_id"),
            "plan_summary": response.get("plan_summary"),
            "trace_details": trace_details,
            "trace_summary": response.get("trace_summary"),
            "suggestions": response.get("suggestions", []),
            "analysis": response.get("analysis", ""),
            "show_traces": response.get("show_traces", False),
            "cached": response.get("cached", False),
            "execution_details": {
                "steps_completed": response.get("plan_summary", {}).get("completed_steps"),
                "total_steps": response.get("plan_summary", {}).get("total_steps"),
                "execution_time_ms": response.get("plan_summary", {}).get("execution_time_ms")
            }
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

@app.get("/memory/{user_id}/threads/{thread_id}/messages")
def get_thread_messages(user_id: str, thread_id: str, limit: int = 50):
    """Get messages from a specific conversation thread"""
    
    try:
        messages = memory_aware_agent.get_thread_messages(user_id, thread_id, limit)
        return {"messages": messages}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/memory/{user_id}/threads/new")
def create_new_thread(user_id: str, title: str = None):
    """Create a new conversation thread explicitly"""
    
    try:
        import time
        from datetime import datetime
        from database.connection import db_manager
        
        # Create new thread manually since we simplified the memory manager
        thread_id = f"thread_{user_id}_{int(time.time())}"
        if not title:
            title = f"Chat {datetime.now().strftime('%m-%d %H:%M')}"
        
        # Deactivate existing threads
        db_manager.execute_query("""
            UPDATE conversation_threads SET is_active = 0 WHERE user_id = ?
        """, (user_id,))
        
        # Create new thread
        db_manager.execute_query("""
            INSERT OR IGNORE INTO conversation_threads (thread_id, user_id, title, is_active)
            VALUES (?, ?, ?, 1)
        """, (thread_id, user_id, title))
        
        return {"success": True, "thread_id": thread_id, "message": f"Created new thread {thread_id}"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# LLM Provider Management Endpoints

@app.get("/llm/status")
def get_llm_status():
    """Get current LLM provider status and available providers"""
    
    try:
        from backend.config.llm_config import LLMConfigManager
        status = LLMConfigManager.get_provider_status()
        return status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/llm/switch/{provider_name}")
def switch_llm_provider(provider_name: str):
    """Switch to a different LLM provider"""
    
    try:
        from backend.core.llm_provider import llm_manager
        
        success = llm_manager.switch_provider(provider_name)
        if success:
            return {
                "success": True,
                "message": f"Switched to {provider_name}",
                "current_provider": llm_manager.get_current_provider()
            }
        else:
            return {
                "success": False,
                "message": f"Failed to switch to {provider_name}",
                "current_provider": llm_manager.get_current_provider()
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/llm/test/{provider_name}")
def test_llm_provider(provider_name: str):
    """Test a specific LLM provider"""
    
    try:
        from backend.core.llm_provider import llm_manager
        
        # Save current provider
        original_provider = llm_manager.get_current_provider()
        
        # Switch to test provider
        llm_manager.switch_provider(provider_name)
        
        # Test with simple prompt
        test_prompt = "Respond with exactly: 'LLM test successful'"
        response = llm_manager.generate_response(test_prompt)
        
        # Switch back to original provider
        if original_provider:
            for provider in llm_manager.providers:
                if provider.get_provider_name() == original_provider:
                    llm_manager.current_provider = provider
                    break
        
        return {
            "success": True,
            "provider": provider_name,
            "test_response": response,
            "message": f"{provider_name} is working correctly"
        }
        
    except Exception as e:
        return {
            "success": False,
            "provider": provider_name,
            "error": str(e),
            "message": f"{provider_name} test failed"
        }

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)